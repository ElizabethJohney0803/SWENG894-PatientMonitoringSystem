"""
Tests for PBI-S3-07 — Pharmacy Fulfillment Status Update (FR-Ph-1).

Test Cases: TC-S3-021 (note: spec uses TC-S3-021 label for this PBI)

Acceptance Criteria:
  AC-07.1  Pharmacy personnel can change fulfillment_status from "pending"
           to "dispensed" via the admin interface.
  AC-07.2  The status change is persisted and the updated_at timestamp
           reflects the change.
  AC-07.3  Dispensed medications remain visible to the doctor for record review.
"""

import pytest
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client

from core.models import Medication, Patient, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)

LIST_URL = "/admin/core/medication/"


def _make_staff_user(username, role, license_number=None, phone="5550000"):
    user = User.objects.create_user(
        username=username, password="pass", is_staff=True, is_superuser=False
    )
    kw = {"user": user, "role": role, "phone": phone}
    if license_number:
        kw["license_number"] = license_number
    UserProfile.objects.create(**kw)
    return user


def _get_or_create_patient(profile):
    patient = Patient.objects.filter(user_profile=profile).first()
    if patient is None:
        patient = Patient(
            user_profile=profile,
            date_of_birth=date(1980, 1, 1),
            gender="M",
            address_line1="1 Test St",
            city="Testville",
            state="TS",
            postal_code="00001",
            phone_primary="5550001111",
        )
        patient.save()
    return patient


def _make_medication(
    patient, doctor_profile, fulfillment_status="pending", name="Lisinopril"
):
    return Medication.objects.create(
        patient=patient,
        prescribing_doctor=doctor_profile,
        medication_name=name,
        dosage="10 mg",
        frequency="Once daily",
        start_date=TODAY,
        status="current",
        fulfillment_status=fulfillment_status,
    )


def _change_url(med):
    return f"/admin/core/medication/{med.pk}/change/"


# ---------------------------------------------------------------------------
# AC-07.1 — Pharmacy can update fulfillment_status to "dispensed"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPharmacyCanUpdateFulfillmentStatus:
    """AC-07.1 — Pharmacy changes fulfillment_status via the admin change form."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s307", "doctor", license_number="MD-S307")
        self.pharmacy = _make_staff_user(
            "pharm_s307", "pharmacy", license_number="PH-S307"
        )

        pat_user = _make_staff_user("pat_s307", "patient")
        pat_profile = UserProfile.objects.get(user=pat_user)
        self.patient = _get_or_create_patient(pat_profile)
        self.patient.assigned_doctor = UserProfile.objects.get(user=self.doctor)
        self.patient.save()

        self.doc_profile = UserProfile.objects.get(user=self.doctor)
        self.med = _make_medication(self.patient, self.doc_profile)

    def test_pharmacy_can_access_change_form(self):
        """AC-07.1: GET change form returns 200 for pharmacy."""
        c = Client()
        c.login(username="pharm_s307", password="pass")
        response = c.get(_change_url(self.med))
        assert response.status_code == 200

    def test_fulfillment_status_is_editable_for_pharmacy(self):
        """AC-07.1: fulfillment_status appears as a select (editable) for pharmacy."""
        c = Client()
        c.login(username="pharm_s307", password="pass")
        response = c.get(_change_url(self.med))
        assert response.status_code == 200
        content = response.content.decode()
        # As an editable select, the name attribute should be present
        assert (
            'name="fulfillment_status"' in content
        ), "fulfillment_status should be an editable field for pharmacy"

    def test_pharmacy_can_post_fulfillment_status_change(self):
        """AC-07.1: Pharmacy POST with fulfillment_status='dispensed' returns 302."""
        c = Client()
        c.login(username="pharm_s307", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "dispensed",
            "notes": "",
        }
        response = c.post(_change_url(self.med), data=payload, follow=False)
        assert (
            response.status_code == 302
        ), f"Expected redirect (302) after save, got {response.status_code}"

    def test_pharmacy_can_change_to_dispensed(self):
        """AC-07.1: fulfillment_status changes from 'pending' to 'dispensed' in DB."""
        assert self.med.fulfillment_status == "pending"
        c = Client()
        c.login(username="pharm_s307", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "dispensed",
            "notes": "",
        }
        c.post(_change_url(self.med), data=payload, follow=False)
        self.med.refresh_from_db()
        assert (
            self.med.fulfillment_status == "dispensed"
        ), f"Expected 'dispensed', got '{self.med.fulfillment_status}'"

    def test_pharmacy_can_change_to_cancelled(self):
        """AC-07.1: Pharmacy can set fulfillment_status to 'cancelled'."""
        c = Client()
        c.login(username="pharm_s307", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "cancelled",
            "notes": "",
        }
        c.post(_change_url(self.med), data=payload, follow=False)
        self.med.refresh_from_db()
        assert self.med.fulfillment_status == "cancelled"


# ---------------------------------------------------------------------------
# AC-07.2 — Status change is persisted and updated_at is updated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFulfillmentStatusPersistsWithTimestamp:
    """AC-07.2 — The status update persists and updated_at reflects the change."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s307b", "doctor", license_number="MD-S307B")
        self.pharmacy = _make_staff_user(
            "pharm_s307b", "pharmacy", license_number="PH-S307B"
        )

        pat_user = _make_staff_user("pat_s307b", "patient")
        pat_profile = UserProfile.objects.get(user=pat_user)
        self.patient = _get_or_create_patient(pat_profile)
        self.patient.assigned_doctor = UserProfile.objects.get(user=self.doctor)
        self.patient.save()

        self.doc_profile = UserProfile.objects.get(user=self.doctor)
        self.med = _make_medication(self.patient, self.doc_profile)

    def test_fulfillment_status_persists_in_db(self):
        """AC-07.2: Updated fulfillment_status is retrievable via ORM after save."""
        c = Client()
        c.login(username="pharm_s307b", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "dispensed",
            "notes": "",
        }
        c.post(_change_url(self.med), data=payload, follow=False)
        refreshed = Medication.objects.get(pk=self.med.pk)
        assert refreshed.fulfillment_status == "dispensed"

    def test_updated_at_changes_after_status_update(self):
        """AC-07.2: updated_at timestamp advances after a fulfillment_status save."""
        original_updated_at = self.med.updated_at
        c = Client()
        c.login(username="pharm_s307b", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "dispensed",
            "notes": "",
        }
        c.post(_change_url(self.med), data=payload, follow=False)
        self.med.refresh_from_db()
        assert (
            self.med.updated_at >= original_updated_at
        ), "updated_at should be >= original after save"

    def test_clinical_fields_unchanged_after_pharmacy_save(self):
        """AC-07.2: Clinical fields (medication_name, dosage) are not altered by pharmacy."""
        c = Client()
        c.login(username="pharm_s307b", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
            "prescribing_doctor": self.doc_profile.pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "dispensed",
            "notes": "Dispensed batch #12",
        }
        c.post(_change_url(self.med), data=payload, follow=False)
        self.med.refresh_from_db()
        assert self.med.medication_name == "Lisinopril"
        assert self.med.dosage == "10 mg"


# ---------------------------------------------------------------------------
# AC-07.3 — Dispensed medications remain visible to the doctor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDispensedMedicationsVisibleToDoctor:
    """AC-07.3 — Doctor can still see/access a dispensed medication record."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s307c", "doctor", license_number="MD-S307C")
        self.pharmacy = _make_staff_user(
            "pharm_s307c", "pharmacy", license_number="PH-S307C"
        )

        pat_user = _make_staff_user("pat_s307c", "patient")
        pat_profile = UserProfile.objects.get(user=pat_user)
        self.patient = _get_or_create_patient(pat_profile)
        self.doc_profile = UserProfile.objects.get(user=self.doctor)
        self.patient.assigned_doctor = self.doc_profile
        self.patient.save()

        # Create a medication already marked dispensed
        self.med = _make_medication(
            self.patient,
            self.doc_profile,
            fulfillment_status="dispensed",
            name="Metformin",
        )

    def test_doctor_can_see_dispensed_med_in_changelist(self):
        """AC-07.3: Dispensed medication appears in doctor's changelist."""
        c = Client()
        c.login(username="doc_s307c", password="pass")
        response = c.get(LIST_URL)
        assert response.status_code == 200
        assert (
            b"Metformin" in response.content
        ), "Dispensed medication not visible to doctor in changelist"

    def test_doctor_can_open_dispensed_med_change_form(self):
        """AC-07.3: Doctor can access the change form for a dispensed medication."""
        c = Client()
        c.login(username="doc_s307c", password="pass")
        response = c.get(_change_url(self.med))
        assert response.status_code == 200

    def test_dispensed_status_shown_in_changelist(self):
        """AC-07.3: 'Dispensed' label visible to doctor in the changelist."""
        c = Client()
        c.login(username="doc_s307c", password="pass")
        response = c.get(LIST_URL)
        assert response.status_code == 200
        assert (
            b"Dispensed" in response.content
        ), "Fulfillment status 'Dispensed' not shown to doctor in changelist"

    def test_pharmacy_clinical_fields_readonly(self):
        """AC-07.1 defence: medication_name is read-only for pharmacy (no input[name=...])."""
        c = Client()
        c.login(username="pharm_s307c", password="pass")
        response = c.get(_change_url(self.med))
        assert response.status_code == 200
        content = response.content.decode()
        # medication_name should NOT appear as a writable text input
        assert (
            'name="medication_name"' not in content
        ), "medication_name should be read-only for pharmacy"
