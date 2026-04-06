"""
Tests for PBI-S3-02 — Pharmacy Dosage Notes (FR-Ph-2).

Test Cases: TC-S3-005, TC-S3-006, TC-S3-007

Acceptance Criteria:
  AC-02.1  Pharmacy user can add/edit the notes field and save successfully
  AC-02.2  dosage notes persist in the database and are retrievable via ORM
  AC-02.3  The notes field is NOT visible/accessible to the patient role
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

MEDICATION_LIST_URL = "/admin/core/medication/"


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
            date_of_birth=date(1975, 8, 22),
            gender="F",
            address_line1="789 Pine St",
            city="Capital City",
            state="IL",
            postal_code="62000",
            phone_primary="5550002222",
        )
    patient.allergies = allergies
    patient.save()
    return patient


def _make_medication(patient, name="Aspirin", notes="", doctor=None):
    return Medication.objects.create(
        patient=patient,
        medication_name=name,
        dosage="100 mg",
        frequency="Once daily",
        start_date=YESTERDAY,
        notes=notes,
        prescribing_doctor=doctor,
    )


def _change_url(med):
    return f"/admin/core/medication/{med.pk}/change/"


# ---------------------------------------------------------------------------
# TC-S3-005 — AC-02.1: Pharmacy can save dosage notes via admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestPharmacyCanSaveDosageNotes:
    """TC-S3-005 — Pharmacy user can write to the notes field and save successfully."""

    def test_pharmacy_can_access_medication_change_form(self, create_groups):
        """AC-02.1: Pharmacy user can open (GET) a medication change form."""
        pharmacy = _make_staff_user("pharmacy_s302_001", "pharmacy", "PH-301")
        pat_u = User.objects.create_user(username="patient_s302_001", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550301"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Metformin")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(_change_url(med))
        assert response.status_code == 200

    def test_pharmacy_notes_field_present_in_change_form(self, create_groups):
        """AC-02.1: The notes textarea is rendered in the change form for pharmacy."""
        pharmacy = _make_staff_user("pharmacy_s302_002", "pharmacy", "PH-302")
        pat_u = User.objects.create_user(username="patient_s302_002", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550302"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Lisinopril")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(_change_url(med))
        content = response.content.decode()

        assert response.status_code == 200
        # The notes textarea (or input) should be in the form
        assert 'name="notes"' in content

    def test_pharmacy_can_post_notes_to_medication(self, create_groups):
        """AC-02.1: Posting updated notes via pharmacy redirects (success = HTTP 302)."""
        pharmacy = _make_staff_user("pharmacy_s302_003", "pharmacy", "PH-303")
        pat_u = User.objects.create_user(username="patient_s302_003", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550303"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Atorvastatin")

        client = Client()
        client.force_login(pharmacy)

        post_data = {
            "patient": patient.pk,
            "medication_name": med.medication_name,
            "dosage": med.dosage,
            "frequency": med.frequency,
            "start_date": str(med.start_date),
            "status": med.status,
            "notes": "Dispense with food. Patient confirmed allergies reviewed.",
            # Required for Django admin save
            "_save": "Save",
        }
        response = client.post(_change_url(med), post_data)
        # 302 = successful save and redirect to changelist
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# TC-S3-006 — AC-02.2: Dosage notes persist in the database
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
class TestDosageNotesPersist:
    """TC-S3-006 — Notes saved to a Medication are retrievable via the ORM."""

    def test_notes_persist_on_create(self, create_groups):
        """AC-02.2: Notes set at creation time persist in the database."""
        pat_u = User.objects.create_user(username="patient_s302_004", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550304"
        )
        patient = _get_or_create_patient(pat_profile)
        note_text = "Take with water. Do not crush."
        med = _make_medication(patient, "Omeprazole", notes=note_text)

        med.refresh_from_db()
        assert med.notes == note_text

    def test_notes_persist_after_update(self, create_groups):
        """AC-02.2: Updated notes are persisted and retrievable after save."""
        pat_u = User.objects.create_user(username="patient_s302_005", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550305"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Amoxicillin", notes="Initial note.")

        updated_note = "Dispensed 30-day supply. Patient counselled on side effects."
        med.notes = updated_note
        med.save()

        med.refresh_from_db()
        assert med.notes == updated_note

    def test_notes_blank_by_default(self, create_groups):
        """AC-02.2: notes field defaults to blank (no stale data)."""
        pat_u = User.objects.create_user(username="patient_s302_006", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550306"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Ibuprofen")  # no notes arg

        med.refresh_from_db()
        assert med.notes == ""

    def test_pharmacy_admin_post_notes_persist_in_db(self, create_groups):
        """AC-02.2: Notes submitted via admin POST are persisted and ORM-retrievable."""
        pharmacy = _make_staff_user("pharmacy_s302_007", "pharmacy", "PH-307")
        pat_u = User.objects.create_user(username="patient_s302_007", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550307"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Warfarin")

        expected_note = "INR monitored. Dispense 90-tablet pack."
        client = Client()
        client.force_login(pharmacy)

        client.post(
            _change_url(med),
            {
                "patient": patient.pk,
                "medication_name": med.medication_name,
                "dosage": med.dosage,
                "frequency": med.frequency,
                "start_date": str(med.start_date),
                "status": med.status,
                "notes": expected_note,
                "_save": "Save",
            },
        )

        med.refresh_from_db()
        assert med.notes == expected_note


# ---------------------------------------------------------------------------
# TC-S3-007 — AC-02.3: notes field is NOT visible to the patient role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientCannotSeeNotesField:
    """TC-S3-007 — Patient role cannot see the notes field in any medication view."""

    def test_patient_cannot_access_medication_admin_at_all(self, create_groups):
        """AC-02.3: Patient hitting the medication list is denied (302/403)."""
        pat_u = User.objects.create_user(
            username="patient_s302_008", password="pass", is_staff=True
        )
        UserProfile.objects.create(user=pat_u, role="patient", phone="5550308")

        client = Client()
        client.force_login(pat_u)
        response = client.get(MEDICATION_LIST_URL)
        assert response.status_code in (302, 403)

    def test_patient_cannot_access_medication_change_form(self, create_groups):
        """AC-02.3: Patient is denied access to a specific medication change view."""
        # Create a medication owned by a different patient
        owner_u = User.objects.create_user(
            username="patient_s302_owner", password="pass"
        )
        owner_profile = UserProfile.objects.create(
            user=owner_u, role="patient", phone="5550309"
        )
        owner_patient = _get_or_create_patient(owner_profile)
        med = _make_medication(
            owner_patient, "Penicillin", notes="Allergic patient — DO NOT DISPENSE"
        )

        # Attacker patient with is_staff=True tries to access it
        attacker_u = User.objects.create_user(
            username="patient_s302_attacker", password="pass", is_staff=True
        )
        UserProfile.objects.create(user=attacker_u, role="patient", phone="5550310")

        client = Client()
        client.force_login(attacker_u)
        response = client.get(_change_url(med))
        # Must be denied — patient cannot read another patient's medication
        assert response.status_code in (302, 403)

    def test_notes_content_absent_when_patient_denied(self, create_groups):
        """AC-02.3: The notes content is not included in the denied response body."""
        owner_u = User.objects.create_user(
            username="patient_s302_owner2", password="pass"
        )
        owner_profile = UserProfile.objects.create(
            user=owner_u, role="patient", phone="5550311"
        )
        owner_patient = _get_or_create_patient(owner_profile)
        secret_note = "PHARMACY_ONLY_SECRET_INSTRUCTION_XYZ"
        med = _make_medication(owner_patient, "Codeine", notes=secret_note)

        attacker_u = User.objects.create_user(
            username="patient_s302_attacker2", password="pass", is_staff=True
        )
        UserProfile.objects.create(user=attacker_u, role="patient", phone="5550312")

        client = Client()
        client.force_login(attacker_u)
        response = client.get(_change_url(med))
        # The secret note must never appear in the response
        assert secret_note not in response.content.decode()
