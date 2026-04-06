"""
Unit tests for PBI-S3-04 — Automatic Allergy Conflict Detection (FR-Ph-4).

Test Cases: TC-S3-011, TC-S3-012, TC-S3-013, TC-S3-014

Acceptance Criteria:
  AC-04.1  allergy_conflict=True when medication name matches a patient allergy
  AC-04.2  allergy_conflict=False when no match exists
  AC-04.3  Check is case-insensitive
  AC-04.4  Blank allergies field produces no false positives
"""

import pytest
from datetime import date

from core.models import Medication, Patient, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patient(user_profile, allergies=""):
    patient = Patient.objects.filter(user_profile=user_profile).first()
    if patient is None:
        patient = Patient(
            user_profile=user_profile,
            date_of_birth=date(1990, 6, 15),
            gender="M",
            address_line1="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            phone_primary="5550001234",
        )
    patient.allergies = allergies
    patient.save()
    return patient


def _make_medication(patient, medication_name, doctor=None):
    return Medication.objects.create(
        patient=patient,
        medication_name=medication_name,
        dosage="500 mg",
        frequency="Once daily",
        start_date=date.today(),
        prescribing_doctor=doctor,
    )


# ---------------------------------------------------------------------------
# TC-S3-011 — AC-04.1: conflict detected when allergy matches medication name
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAllergyConflictDetected:
    """TC-S3-011 — allergy_conflict is True when there is a match."""

    def test_allergy_conflict_set_true_on_save(self, patient_user):
        """AC-04.1: Saving a Medication whose name is in patient allergies sets allergy_conflict=True."""
        patient = _make_patient(patient_user.profile, allergies="Penicillin, Aspirin")
        med = _make_medication(patient, medication_name="Penicillin")

        assert med.allergy_conflict is True

    def test_allergy_conflict_true_for_substring_allergy(self, patient_user):
        """AC-04.1: Match works when allergy entry is a substring of the medication name."""
        patient = _make_patient(patient_user.profile, allergies="sulfa")
        med = _make_medication(patient, medication_name="Sulfamethoxazole")

        assert med.allergy_conflict is True

    def test_allergy_conflict_true_with_multiple_allergies(self, patient_user):
        """AC-04.1: Conflict detected when one of several allergies matches."""
        patient = _make_patient(
            patient_user.profile, allergies="Latex, Ibuprofen, Codeine"
        )
        med = _make_medication(patient, medication_name="Ibuprofen")

        assert med.allergy_conflict is True

    def test_allergy_conflict_flag_persists_in_db(self, patient_user):
        """AC-04.1: allergy_conflict=True is persisted and retrievable via ORM."""
        patient = _make_patient(patient_user.profile, allergies="Aspirin")
        med = _make_medication(patient, medication_name="Aspirin")

        med.refresh_from_db()
        assert med.allergy_conflict is True


# ---------------------------------------------------------------------------
# TC-S3-012 — AC-04.2: no conflict when medication name does not match any allergy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestNoAllergyConflict:
    """TC-S3-012 — allergy_conflict is False when there is no match."""

    def test_allergy_conflict_false_when_no_match(self, patient_user):
        """AC-04.2: allergy_conflict=False when medication name doesn't match any allergy."""
        patient = _make_patient(patient_user.profile, allergies="Penicillin, Aspirin")
        med = _make_medication(patient, medication_name="Metformin")

        assert med.allergy_conflict is False

    def test_allergy_conflict_false_persists_in_db(self, patient_user):
        """AC-04.2: allergy_conflict=False is persisted and retrievable via ORM."""
        patient = _make_patient(patient_user.profile, allergies="Latex")
        med = _make_medication(patient, medication_name="Amoxicillin")

        med.refresh_from_db()
        assert med.allergy_conflict is False

    def test_allergy_conflict_recalculated_on_update(self, patient_user):
        """AC-04.2: allergy_conflict is recalculated on every save; updating medication
        name away from a conflicting value clears the flag."""
        patient = _make_patient(patient_user.profile, allergies="Aspirin")
        med = _make_medication(patient, medication_name="Aspirin")
        assert med.allergy_conflict is True

        med.medication_name = "Metformin"
        med.save()
        assert med.allergy_conflict is False


# ---------------------------------------------------------------------------
# TC-S3-013 — AC-04.3: check is case-insensitive
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAllergyConflictCaseInsensitive:
    """TC-S3-013 — case-insensitive matching."""

    def test_allergy_uppercase_medication_lowercase(self, patient_user):
        """AC-04.3: Allergy stored in UPPERCASE matches lowercase medication name."""
        patient = _make_patient(patient_user.profile, allergies="PENICILLIN")
        med = _make_medication(patient, medication_name="penicillin")
        assert med.allergy_conflict is True

    def test_allergy_lowercase_medication_uppercase(self, patient_user):
        """AC-04.3: Allergy stored in lowercase matches UPPERCASE medication name."""
        patient = _make_patient(patient_user.profile, allergies="aspirin")
        med = _make_medication(patient, medication_name="ASPIRIN")
        assert med.allergy_conflict is True

    def test_allergy_mixed_case(self, patient_user):
        """AC-04.3: Mixed-case allergy and medication name still match."""
        patient = _make_patient(patient_user.profile, allergies="Ibuprofen")
        med = _make_medication(patient, medication_name="IBUPROFEN")
        assert med.allergy_conflict is True

    def test_no_false_positive_different_drug_same_case(self, patient_user):
        """AC-04.3: Case-insensitive match does not produce false positives for different names."""
        patient = _make_patient(patient_user.profile, allergies="PENICILLIN")
        med = _make_medication(patient, medication_name="METFORMIN")
        assert med.allergy_conflict is False


# ---------------------------------------------------------------------------
# TC-S3-014 — AC-04.4: blank allergies field produces no false positives
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestBlankAllergiesNoFalsePositive:
    """TC-S3-014 — blank/empty allergies field never triggers a conflict."""

    def test_blank_allergies_no_conflict(self, patient_user):
        """AC-04.4: allergy_conflict=False when patient allergies field is blank."""
        patient = _make_patient(patient_user.profile, allergies="")
        med = _make_medication(patient, medication_name="Penicillin")
        assert med.allergy_conflict is False

    def test_whitespace_only_allergies_no_conflict(self, patient_user):
        """AC-04.4: Whitespace-only allergies field is treated as blank (no false positives)."""
        patient = _make_patient(patient_user.profile, allergies="   ")
        med = _make_medication(patient, medication_name="Aspirin")
        assert med.allergy_conflict is False

    def test_null_like_allergies_no_conflict(self, patient_user):
        """AC-04.4: Allergies field left at its default (empty) raises no conflict."""
        patient = _make_patient(patient_user.profile, allergies="")
        med = _make_medication(patient, medication_name="Ibuprofen")
        assert med.allergy_conflict is False
