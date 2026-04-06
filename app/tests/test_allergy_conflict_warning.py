"""
Integration tests for PBI-S3-05 — Allergy Conflict Warning Display (FR-Ph-5).

Test Cases: TC-S3-015, TC-S3-016, TC-S3-017

Acceptance Criteria:
  AC-05.1  Warning rendered in admin for allergy_conflict=True medications
  AC-05.2  No warning rendered for allergy_conflict=False medications
  AC-05.3  Warning visible to doctor role as well as pharmacy
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

WARNING_TEXT = "Allergy conflict detected"


def _make_staff_user(username, role, license_number=None):
    user = User.objects.create_user(
        username=username, password="pass", is_staff=True, is_superuser=False
    )
    profile_kwargs = {"user": user, "role": role}
    if license_number:
        profile_kwargs["license_number"] = license_number
    UserProfile.objects.create(**profile_kwargs)
    return user


def _get_or_create_patient(user_profile, allergies=""):
    patient = Patient.objects.filter(user_profile=user_profile).first()
    if patient is None:
        patient = Patient(
            user_profile=user_profile,
            date_of_birth=date(1985, 3, 20),
            gender="F",
            address_line1="456 Elm St",
            city="Shelbyville",
            state="IL",
            postal_code="62565",
            phone_primary="5550009999",
        )
    patient.allergies = allergies
    patient.save()
    return patient


def _make_medication(patient, medication_name, doctor=None):
    return Medication.objects.create(
        patient=patient,
        medication_name=medication_name,
        dosage="250 mg",
        frequency="Twice daily",
        start_date=YESTERDAY,
        prescribing_doctor=doctor,
    )


# ---------------------------------------------------------------------------
# TC-S3-015 — AC-05.1: Warning shown in list view and change view when
#             allergy_conflict=True (pharmacy role)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestAllergyConflictWarningShown:
    """TC-S3-015 — Warning visible in admin when allergy_conflict=True."""

    def _setup_conflicting_med(self, create_groups):
        pat_user = User.objects.create_user(
            username="patient_ac05_001", password="pass"
        )
        patient_profile = UserProfile.objects.create(
            user=pat_user, role="patient", phone="5550001"
        )
        patient = _get_or_create_patient(patient_profile, allergies="Penicillin")
        pharmacy = _make_staff_user("pharmacy_ac05_001", "pharmacy", "PH-001")
        med = _make_medication(patient, "Penicillin")
        return pharmacy, med

    def test_warning_appears_in_changelist_for_pharmacy(self, create_groups):
        """AC-05.1: Pharmacy sees warning indicator in medication list."""
        pharmacy, med = self._setup_conflicting_med(create_groups)
        assert med.allergy_conflict is True

        client = Client()
        client.force_login(pharmacy)
        response = client.get("/admin/core/medication/")
        assert response.status_code == 200
        assert WARNING_TEXT in response.content.decode()

    def test_warning_appears_in_change_view_for_pharmacy(self, create_groups):
        """AC-05.1: Pharmacy sees warning banner in the medication change form."""
        pharmacy, med = self._setup_conflicting_med(create_groups)

        client = Client()
        client.force_login(pharmacy)
        response = client.get(f"/admin/core/medication/{med.pk}/change/")
        assert response.status_code == 200
        assert WARNING_TEXT in response.content.decode()


# ---------------------------------------------------------------------------
# TC-S3-016 — AC-05.2: No warning shown when allergy_conflict=False
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestAllergyConflictWarningAbsent:
    """TC-S3-016 — No warning displayed when allergy_conflict=False."""

    def _setup_safe_med(self, create_groups):
        pat_user = User.objects.create_user(
            username="patient_ac05_002", password="pass"
        )
        patient_profile = UserProfile.objects.create(
            user=pat_user, role="patient", phone="5550002"
        )
        patient = _get_or_create_patient(patient_profile, allergies="Latex")
        pharmacy = _make_staff_user("pharmacy_ac05_002", "pharmacy", "PH-002")
        # Metformin does not match "Latex"
        med = _make_medication(patient, "Metformin")
        return pharmacy, med

    def test_no_warning_in_changelist_for_safe_medication(self, create_groups):
        """AC-05.2: No warning in list when medication does not conflict."""
        pharmacy, med = self._setup_safe_med(create_groups)
        assert med.allergy_conflict is False

        client = Client()
        client.force_login(pharmacy)
        response = client.get("/admin/core/medication/")
        assert response.status_code == 200
        assert WARNING_TEXT not in response.content.decode()

    def test_no_warning_in_change_view_for_safe_medication(self, create_groups):
        """AC-05.2: No warning banner in change form when medication does not conflict."""
        pharmacy, med = self._setup_safe_med(create_groups)

        client = Client()
        client.force_login(pharmacy)
        response = client.get(f"/admin/core/medication/{med.pk}/change/")
        assert response.status_code == 200
        assert WARNING_TEXT not in response.content.decode()

    def test_no_warning_when_allergies_blank(self, create_groups):
        """AC-05.2 / AC-04.4: No warning when patient allergies field is blank."""
        pat_user = User.objects.create_user(
            username="patient_ac05_003", password="pass"
        )
        patient_profile = UserProfile.objects.create(
            user=pat_user, role="patient", phone="5550003"
        )
        patient = _get_or_create_patient(patient_profile, allergies="")
        pharmacy = _make_staff_user("pharmacy_ac05_003", "pharmacy", "PH-003")
        med = _make_medication(patient, "Aspirin")
        assert med.allergy_conflict is False

        client = Client()
        client.force_login(pharmacy)
        response = client.get("/admin/core/medication/")
        assert response.status_code == 200
        assert WARNING_TEXT not in response.content.decode()


# ---------------------------------------------------------------------------
# TC-S3-017 — AC-05.3: Warning visible to doctor role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestAllergyConflictWarningVisibleToDoctor:
    """TC-S3-017 — Warning visible to doctor role (not only pharmacy)."""

    def _setup(self, create_groups):
        doctor = _make_staff_user("doctor_ac05_001", "doctor", "MD-001")
        pat_user = User.objects.create_user(
            username="patient_ac05_004", password="pass"
        )
        patient_profile = UserProfile.objects.create(
            user=pat_user, role="patient", phone="5550004"
        )
        patient = _get_or_create_patient(patient_profile, allergies="Codeine")
        # Assign patient to doctor so they appear in the doctor's queryset
        patient.assigned_doctor = doctor.profile
        patient.save()
        med = _make_medication(patient, "Codeine", doctor=doctor.profile)
        return doctor, med

    def test_warning_in_changelist_for_doctor(self, create_groups):
        """AC-05.3: Doctor sees warning indicator in medication list for conflicting med."""
        doctor, med = self._setup(create_groups)
        assert med.allergy_conflict is True

        client = Client()
        client.force_login(doctor)
        response = client.get("/admin/core/medication/")
        assert response.status_code == 200
        assert WARNING_TEXT in response.content.decode()

    def test_warning_in_change_view_for_doctor(self, create_groups):
        """AC-05.3: Doctor sees warning banner in change form for conflicting med."""
        doctor, med = self._setup(create_groups)

        client = Client()
        client.force_login(doctor)
        response = client.get(f"/admin/core/medication/{med.pk}/change/")
        assert response.status_code == 200
        assert WARNING_TEXT in response.content.decode()

    def test_no_warning_in_change_view_for_doctor_safe_med(self, create_groups):
        """AC-05.3 (negative): Doctor sees no warning for non-conflicting medication."""
        doctor = _make_staff_user("doctor_ac05_002", "doctor", "MD-002")
        pat_user = User.objects.create_user(
            username="patient_ac05_005", password="pass"
        )
        patient_profile = UserProfile.objects.create(
            user=pat_user, role="patient", phone="5550005"
        )
        patient = _get_or_create_patient(patient_profile, allergies="Latex")
        patient.assigned_doctor = doctor.profile
        patient.save()
        med = _make_medication(patient, "Metformin", doctor=doctor.profile)
        assert med.allergy_conflict is False

        client = Client()
        client.force_login(doctor)
        response = client.get(f"/admin/core/medication/{med.pk}/change/")
        assert response.status_code == 200
        assert WARNING_TEXT not in response.content.decode()
