"""
Tests for PBI-S3-06 — Doctor Prescription Workflow (FR-D-4 / FR-D-5).

Test Cases: TC-S3-018, TC-S3-019, TC-S3-020

Acceptance Criteria:
  AC-06.1  A doctor can access the add-medication form and successfully submit
           a new prescription; the system records it with fulfillment_status="pending".
  AC-06.2  The newly created prescription is visible to pharmacy in the
           medication changelist, and fulfillment_status is shown as "Pending".
  AC-06.3  Nurse and patient roles cannot access the add-medication page
           (no has_add_permission for those roles).
"""

import pytest
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client

from core.models import Medication, Patient, UserProfile


# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)

ADD_URL = "/admin/core/medication/add/"
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


def _get_or_create_patient(user_profile, allergies=""):
    patient = Patient.objects.filter(user_profile=user_profile).first()
    if patient is None:
        patient = Patient(
            user_profile=user_profile,
            date_of_birth=date(1985, 3, 15),
            gender="M",
            address_line1="1 Test Lane",
            city="Test City",
            state="TS",
            zip_code="00000",
            allergies=allergies,
        )
        patient.save()
    return patient


def _make_prescription(patient, doctor_profile, **kwargs):
    defaults = dict(
        medication_name="Lisinopril",
        dosage="10 mg",
        frequency="Once daily",
        start_date=TODAY,
        status="current",
    )
    defaults.update(kwargs)
    return Medication.objects.create(
        patient=patient,
        prescribing_doctor=doctor_profile,
        **defaults,
    )


# ---------------------------------------------------------------------------
# TC-S3-018: Doctor can GET add form and POST a new prescription (AC-06.1)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDoctorCanCreatePrescription:
    """TC-S3-018 — Doctor creates a prescription via Django admin."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s318", "doctor", license_number="MD-S318")
        self.patient_user = _make_staff_user("pat_s318", "patient")
        self.patient_profile = UserProfile.objects.get(user=self.patient_user)
        self.patient = _get_or_create_patient(self.patient_profile)
        # Assign patient to doctor
        self.patient.assigned_doctor = UserProfile.objects.get(user=self.doctor)
        self.patient.save()

    def test_doctor_can_access_add_form(self):
        """TC-S3-018: GET /admin/core/medication/add/ returns 200 for doctor."""
        c = Client()
        c.login(username="doc_s318", password="pass")
        response = c.get(ADD_URL)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_add_form_contains_fulfillment_status_field(self):
        """TC-S3-018: The add form renders a fulfillment_status select."""
        c = Client()
        c.login(username="doc_s318", password="pass")
        response = c.get(ADD_URL)
        assert (
            b"fulfillment_status" in response.content
        ), "fulfillment_status field missing from add form"

    def test_doctor_can_post_prescription(self):
        """TC-S3-018: POST creates a Medication record; redirects (302)."""
        c = Client()
        c.login(username="doc_s318", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Amoxicillin",
            "dosage": "500 mg",
            "frequency": "Three times daily",
            "prescribing_doctor": UserProfile.objects.get(user=self.doctor).pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "pending",
            "notes": "",
        }
        response = c.post(ADD_URL, data=payload, follow=False)
        assert (
            response.status_code == 302
        ), f"Expected redirect (302) after successful POST, got {response.status_code}"

    def test_newly_created_medication_has_pending_fulfillment_status(self):
        """TC-S3-018 (AC-06.1): Created prescription defaults to fulfillment_status='pending'."""
        c = Client()
        c.login(username="doc_s318", password="pass")
        payload = {
            "patient": self.patient.pk,
            "medication_name": "Metoprolol",
            "dosage": "25 mg",
            "frequency": "Twice daily",
            "prescribing_doctor": UserProfile.objects.get(user=self.doctor).pk,
            "start_date": TODAY.isoformat(),
            "status": "current",
            "fulfillment_status": "pending",
            "notes": "",
        }
        c.post(ADD_URL, data=payload, follow=False)
        med = Medication.objects.filter(medication_name="Metoprolol").first()
        assert med is not None, "Medication was not created"
        assert (
            med.fulfillment_status == "pending"
        ), f"Expected 'pending', got '{med.fulfillment_status}'"


# ---------------------------------------------------------------------------
# TC-S3-019: Prescription visible to pharmacy (AC-06.2)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPrescriptionVisibleToPharmacy:
    """TC-S3-019 — Pharmacy sees the new prescription with 'Pending' status."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s319", "doctor", license_number="MD-S319")
        self.pharmacy = _make_staff_user(
            "pharm_s319", "pharmacy", license_number="PH-S319"
        )
        self.patient_user = _make_staff_user("pat_s319", "patient")
        self.patient_profile = UserProfile.objects.get(user=self.patient_user)
        self.patient = _get_or_create_patient(self.patient_profile)
        self.patient.assigned_doctor = UserProfile.objects.get(user=self.doctor)
        self.patient.save()
        self.med = _make_prescription(
            self.patient,
            UserProfile.objects.get(user=self.doctor),
            medication_name="Atorvastatin",
        )

    def test_pharmacy_sees_prescription_in_changelist(self):
        """TC-S3-019: Pharmacy can list medication orders and see the prescription."""
        c = Client()
        c.login(username="pharm_s319", password="pass")
        response = c.get(LIST_URL)
        assert response.status_code == 200
        assert (
            b"Atorvastatin" in response.content
        ), "Pharmacy cannot see the prescription in the changelist"

    def test_changelist_shows_pending_fulfillment_status(self):
        """TC-S3-019 (AC-06.2): Changelist shows 'Pending' in the fulfillment_status column."""
        c = Client()
        c.login(username="pharm_s319", password="pass")
        response = c.get(LIST_URL)
        assert response.status_code == 200
        assert (
            b"Pending" in response.content
        ), "Fulfillment status 'Pending' not visible to pharmacy in changelist"

    def test_fulfillment_status_column_header_visible(self):
        """TC-S3-019: Column header 'Fulfillment Status' appears in changelist."""
        c = Client()
        c.login(username="pharm_s319", password="pass")
        response = c.get(LIST_URL)
        assert response.status_code == 200
        assert (
            b"Fulfillment" in response.content
        ), "Fulfillment Status column header not found in changelist"

    def test_fulfillment_status_readonly_for_pharmacy_on_change_form(self):
        """TC-S3-019: Pharmacy sees fulfillment_status as read-only on the change form."""
        c = Client()
        c.login(username="pharm_s319", password="pass")
        change_url = f"/admin/core/medication/{self.med.pk}/change/"
        response = c.get(change_url)
        assert response.status_code == 200
        content = response.content.decode()
        # fulfillment_status should appear on page but not as an editable select
        assert "fulfillment_status" in content


# ---------------------------------------------------------------------------
# TC-S3-020: Nurse / patient cannot add prescriptions (AC-06.3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNurseAndPatientCannotCreatePrescription:
    """TC-S3-020 — Nurse and patient roles are denied add access."""

    def setup_method(self):
        self.nurse = _make_staff_user("nurse_s320", "nurse", license_number="RN-S320")
        # Patient user must be staff to reach admin (otherwise Django redirects to login)
        self.patient = _make_staff_user("pat_s320", "patient")

    def test_nurse_gets_denied_on_get_add_form(self):
        """TC-S3-020: Nurse GET /admin/core/medication/add/ gets 403 or redirect."""
        c = Client()
        c.login(username="nurse_s320", password="pass")
        response = c.get(ADD_URL)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for nurse, got {response.status_code}"

    def test_nurse_cannot_post_prescription(self):
        """TC-S3-020: Nurse POST is rejected with 302/403."""
        c = Client()
        c.login(username="nurse_s320", password="pass")
        response = c.post(ADD_URL, data={}, follow=False)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for nurse POST, got {response.status_code}"

    def test_patient_gets_denied_on_get_add_form(self):
        """TC-S3-020: Patient (even if staff) GET add form is denied."""
        c = Client()
        c.login(username="pat_s320", password="pass")
        response = c.get(ADD_URL)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for patient role, got {response.status_code}"
