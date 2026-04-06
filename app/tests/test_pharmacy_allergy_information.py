"""
Tests for PBI-S3-03 — Pharmacy Allergy Information View (FR-Ph-3).

Test Cases: TC-S3-008, TC-S3-009, TC-S3-010

Acceptance Criteria:
  AC-03.1  The `allergies` field from the Patient record is visible to pharmacy
           personnel in the patient detail (change) view.
  AC-03.2  The `allergies` field is NOT visible to the patient role in their
           own admin view.
  AC-03.3  The `allergies` field is visible to doctor, nurse, and admin roles
           when viewing a patient record.
"""

import pytest
from datetime import date

from django.contrib.auth.models import User
from django.test import Client

from core.models import Patient, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PATIENT_LIST_URL = "/admin/core/patient/"


def _make_staff_user(username, role, license_number=None, phone="5550000"):
    user = User.objects.create_user(
        username=username, password="pass", is_staff=True, is_superuser=False
    )
    kw = {"user": user, "role": role, "phone": phone}
    if license_number:
        kw["license_number"] = license_number
    UserProfile.objects.create(**kw)
    return user


def _make_patient_record(profile, allergies="Penicillin, Aspirin"):
    patient = Patient.objects.filter(user_profile=profile).first()
    if patient is None:
        patient = Patient(
            user_profile=profile,
            date_of_birth=date(1980, 6, 15),
            gender="M",
            address_line1="1 Allergy Lane",
            city="Test City",
            state="TC",
            postal_code="11111",
            phone_primary="5550009999",
        )
    patient.allergies = allergies
    patient.save()
    return patient


def _change_url(patient):
    return f"/admin/core/patient/{patient.pk}/change/"


# ---------------------------------------------------------------------------
# TC-S3-008 — AC-03.1: Pharmacy can see allergies in patient detail view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPharmacySeeAllergies:
    """TC-S3-008 — Pharmacy views patient detail and sees the allergies field."""

    def setup_method(self):
        self.pharmacy = _make_staff_user(
            "pharm_s308", "pharmacy", license_number="PH-S308"
        )
        # Create a separate user as the patient whose record will be viewed
        self.patient_user = _make_staff_user("pat_s308", "patient")
        self.patient_profile = UserProfile.objects.get(user=self.patient_user)
        self.patient = _make_patient_record(
            self.patient_profile, allergies="Penicillin, Sulfa"
        )

    def test_pharmacy_can_access_patient_change_form(self):
        """TC-S3-008: Pharmacy GET on patient change form returns 200."""
        c = Client()
        c.login(username="pharm_s308", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_pharmacy_sees_allergy_information_section(self):
        """TC-S3-008: 'Allergy Information' fieldset heading is present."""
        c = Client()
        c.login(username="pharm_s308", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        assert (
            b"Allergy Information" in response.content
        ), "Pharmacy does not see the 'Allergy Information' section heading"

    def test_pharmacy_sees_allergy_values(self):
        """TC-S3-008 (AC-03.1): Pharmacy sees actual allergy text in the detail view."""
        c = Client()
        c.login(username="pharm_s308", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        content = response.content.decode()
        assert (
            "Penicillin" in content
        ), "Allergy value 'Penicillin' not visible to pharmacy in patient detail"

    def test_pharmacy_sees_allergies_field_in_patient_list(self):
        """TC-S3-008: Pharmacy can access the patient changelist (not denied)."""
        c = Client()
        c.login(username="pharm_s308", password="pass")
        response = c.get(PATIENT_LIST_URL)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TC-S3-009 — AC-03.2: Patient role cannot see allergies in own admin view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPatientCannotSeeAllergies:
    """TC-S3-009 — Patient role's own admin view does not expose allergies."""

    def setup_method(self):
        # Patient user must be staff to reach the admin at all
        self.patient_user = _make_staff_user("pat_s309", "patient")
        self.patient_profile = UserProfile.objects.get(user=self.patient_user)
        self.patient = _make_patient_record(
            self.patient_profile, allergies="Penicillin, Aspirin"
        )

    def test_patient_can_access_own_change_form(self):
        """TC-S3-009: Patient can access their own change form (HTTP 200)."""
        c = Client()
        c.login(username="pat_s309", password="pass")
        response = c.get(_change_url(self.patient))
        assert (
            response.status_code == 200
        ), f"Expected 200 for own record, got {response.status_code}"

    def test_patient_does_not_see_allergies_field(self):
        """TC-S3-009 (AC-03.2): Allergies field is absent from patient's own view."""
        c = Client()
        c.login(username="pat_s309", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        content = response.content.decode()
        # The input/textarea for 'allergies' must not appear
        assert (
            'name="allergies"' not in content
        ), "Patient role should not see an editable 'allergies' field"

    def test_patient_does_not_see_allergy_information_section(self):
        """TC-S3-009 (AC-03.2): 'Allergy Information' section heading absent for patient."""
        c = Client()
        c.login(username="pat_s309", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        assert (
            b"Allergy Information" not in response.content
        ), "Patient role should not see the 'Allergy Information' section"

    def test_patient_does_not_see_medical_history_section(self):
        """TC-S3-009 (AC-03.2): No 'Medical History' section exposed to patient."""
        c = Client()
        c.login(username="pat_s309", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        assert (
            b"Medical History" not in response.content
        ), "Patient role should not see the 'Medical History' section"


# ---------------------------------------------------------------------------
# TC-S3-010 — AC-03.3: Doctor, nurse, and admin see allergies
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDoctorNurseAdminSeeAllergies:
    """TC-S3-010 — Doctor, nurse, and admin roles all see allergies in patient detail."""

    def setup_method(self):
        self.doctor = _make_staff_user("doc_s310", "doctor", license_number="MD-S310")
        self.nurse = _make_staff_user("nurse_s310", "nurse", license_number="RN-S310")
        self.admin = _make_staff_user("admin_s310", "admin")

        # Patient whose record will be viewed
        self.patient_user = _make_staff_user("pat_s310", "patient")
        self.patient_profile = UserProfile.objects.get(user=self.patient_user)
        self.patient = _make_patient_record(
            self.patient_profile, allergies="Sulfa, Latex"
        )

        # Assign patient to doctor and nurse so queryset filtering passes
        self.patient.assigned_doctor = UserProfile.objects.get(user=self.doctor)
        self.patient.assigned_nurse = UserProfile.objects.get(user=self.nurse)
        self.patient.save()

    def test_doctor_sees_allergies(self):
        """TC-S3-010 (AC-03.3): Doctor can read allergies field in patient detail."""
        c = Client()
        c.login(username="doc_s310", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        content = response.content.decode()
        assert (
            "Sulfa" in content
        ), "Doctor should see allergy value 'Sulfa' in patient detail"

    def test_doctor_sees_medical_history_section(self):
        """TC-S3-010: Doctor sees 'Medical History' fieldset heading."""
        c = Client()
        c.login(username="doc_s310", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        assert (
            b"Medical History" in response.content
        ), "Doctor should see the 'Medical History' section"

    def test_nurse_sees_allergies(self):
        """TC-S3-010 (AC-03.3): Nurse can read allergies field in patient detail."""
        c = Client()
        c.login(username="nurse_s310", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        content = response.content.decode()
        assert (
            "Sulfa" in content
        ), "Nurse should see allergy value 'Sulfa' in patient detail"

    def test_admin_sees_allergies(self):
        """TC-S3-010 (AC-03.3): Admin can read allergies field in patient detail."""
        c = Client()
        c.login(username="admin_s310", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        content = response.content.decode()
        assert (
            "Sulfa" in content
        ), "Admin should see allergy value 'Sulfa' in patient detail"

    def test_admin_sees_medical_history_section(self):
        """TC-S3-010: Admin sees 'Medical History' fieldset heading."""
        c = Client()
        c.login(username="admin_s310", password="pass")
        response = c.get(_change_url(self.patient))
        assert response.status_code == 200
        assert b"Medical History" in response.content
