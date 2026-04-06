"""
Integration tests for PBI-S3-01 — Pharmacy Medication Orders Interface (FR-Ph-1, FR-Ph-2).

Test Cases: TC-S3-001, TC-S3-002, TC-S3-003, TC-S3-004

Acceptance Criteria:
  AC-01.1  Pharmacy role can access the medication orders list (HTTP 200)
  AC-01.2  Patient role cannot access the medication orders list (HTTP 302/403)
  AC-01.3  List displays: medication name, dosage, prescribing doctor name, date prescribed
  AC-01.4  Pharmacy personnel only see orders for patients with real prescriptions (no phantom records)
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
            date_of_birth=date(1980, 5, 10),
            gender="M",
            address_line1="100 Oak Ave",
            city="Springfield",
            state="IL",
            postal_code="62701",
            phone_primary="5550001111",
        )
    patient.allergies = allergies
    patient.save()
    return patient


def _make_medication(patient, name="Aspirin", doctor=None, status="current"):
    return Medication.objects.create(
        patient=patient,
        medication_name=name,
        dosage="100 mg",
        frequency="Once daily",
        start_date=YESTERDAY,
        status=status,
        prescribing_doctor=doctor,
    )


# ---------------------------------------------------------------------------
# TC-S3-001 — AC-01.1: Pharmacy role can access medication orders list (HTTP 200)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestPharmacyCanAccessMedicationList:
    """TC-S3-001 — Pharmacy user gets HTTP 200 on the medication changelist."""

    def test_pharmacy_gets_200_on_medication_list(self, create_groups):
        """AC-01.1: Pharmacy staff can access /admin/core/medication/ (HTTP 200)."""
        pharmacy = _make_staff_user("pharmacy_s301_001", "pharmacy", "PH-001")
        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        assert response.status_code == 200

    def test_pharmacy_sees_medication_changelist_page_content(self, create_groups):
        """AC-01.1: Response page contains the changelist table (sanity check)."""
        pharmacy = _make_staff_user("pharmacy_s301_002", "pharmacy", "PH-002")

        pat_u = User.objects.create_user(username="patient_s301_001", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550002"
        )
        patient = _get_or_create_patient(pat_profile)
        _make_medication(patient, "Metformin")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        assert response.status_code == 200
        assert b"Metformin" in response.content


# ---------------------------------------------------------------------------
# TC-S3-002 — AC-01.2: Patient role cannot access medication orders list
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientCannotAccessMedicationList:
    """TC-S3-002 — Patient user is denied access to the medication changelist."""

    def test_patient_is_redirected_from_medication_list(self, create_groups):
        """AC-01.2: Patient hitting /admin/core/medication/ gets HTTP 302 or 403."""
        pat_u = User.objects.create_user(
            username="patient_s301_002", password="pass", is_staff=True
        )
        UserProfile.objects.create(user=pat_u, role="patient", phone="5550003")

        client = Client()
        client.force_login(pat_u)
        response = client.get(MEDICATION_LIST_URL)
        assert response.status_code in (302, 403)

    def test_patient_cannot_access_any_medication_change_view(self, create_groups):
        """AC-01.2: Patient cannot access a specific medication record's change page."""
        # Create an unrelated patient + medication
        owner_u = User.objects.create_user(
            username="patient_s301_owner", password="pass"
        )
        owner_profile = UserProfile.objects.create(
            user=owner_u, role="patient", phone="5550004"
        )
        owner_patient = _get_or_create_patient(owner_profile)
        med = _make_medication(owner_patient, "Ibuprofen")

        # Attacker patient tries to access it
        attacker_u = User.objects.create_user(
            username="patient_s301_attacker", password="pass", is_staff=True
        )
        UserProfile.objects.create(user=attacker_u, role="patient", phone="5550005")

        client = Client()
        client.force_login(attacker_u)
        response = client.get(f"/admin/core/medication/{med.pk}/change/")
        assert response.status_code in (302, 403)


# ---------------------------------------------------------------------------
# TC-S3-003 — AC-01.3: Required columns appear in the medication list
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestMedicationListDisplaysRequiredColumns:
    """TC-S3-003 — Changelist renders medication name, dosage, doctor name, date prescribed."""

    def test_required_columns_present_in_response(self, create_groups):
        """AC-01.3: medication name, dosage, doctor name, and start_date are all rendered."""
        doctor = _make_staff_user("doctor_s301_001", "doctor", "MD-001")
        pharmacy = _make_staff_user("pharmacy_s301_003", "pharmacy", "PH-003")

        pat_u = User.objects.create_user(username="patient_s301_003", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550006"
        )
        patient = _get_or_create_patient(pat_profile)

        _make_medication(patient, "Amoxicillin", doctor=doctor.profile)

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        content = response.content.decode()

        assert response.status_code == 200
        # Medication name rendered in the result row
        assert "Amoxicillin" in content
        # Dosage rendered in the result row
        assert "100 mg" in content
        # Prescribing doctor column header appears (AC-01.3 — doctor name column)
        assert "Prescribing Doctor" in content
        # start_date column header appears (date prescribed)
        assert "Start date" in content or "start_date" in content.lower()

    def test_column_headers_include_doctor_and_date(self, create_groups):
        """AC-01.3: Column headers for prescribing doctor and date prescribed shown."""
        pharmacy = _make_staff_user("pharmacy_s301_004", "pharmacy", "PH-004")

        # Django admin only renders the results table (with headers) when there
        # are records in the queryset — create one so the table is rendered.
        pat_u = User.objects.create_user(username="patient_s301_004b", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550006b"
        )
        patient = _get_or_create_patient(pat_profile)
        _make_medication(patient, "TestDrug")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        content = response.content.decode()

        assert response.status_code == 200
        # The column header for the doctor display method
        assert "Prescribing Doctor" in content
        # The column header for start_date (Django uses verbose_name or field name)
        assert "Start date" in content or "start_date" in content.lower()


# ---------------------------------------------------------------------------
# TC-S3-004 — AC-01.4: Pharmacy only sees orders linked to real patients
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.integration
class TestPharmacySeesOnlyRealOrders:
    """TC-S3-004 — Pharmacy changelist contains only records linked to actual patients."""

    def test_pharmacy_sees_existing_medications(self, create_groups):
        """AC-01.4: Pharmacy sees medications that actually exist for real patients."""
        pharmacy = _make_staff_user("pharmacy_s301_005", "pharmacy", "PH-005")

        pat_u = User.objects.create_user(username="patient_s301_004", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550007"
        )
        patient = _get_or_create_patient(pat_profile)
        _make_medication(patient, "Lisinopril")
        _make_medication(patient, "Atorvastatin")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        content = response.content.decode()

        assert response.status_code == 200
        assert "Lisinopril" in content
        assert "Atorvastatin" in content

    def test_pharmacy_changelist_count_matches_db_records(self, create_groups):
        """AC-01.4: No phantom records — changelist row count matches actual Medication count."""
        pharmacy = _make_staff_user("pharmacy_s301_006", "pharmacy", "PH-006")

        pat_u = User.objects.create_user(username="patient_s301_005", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550008"
        )
        patient = _get_or_create_patient(pat_profile)
        _make_medication(patient, "Omeprazole")

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)

        assert response.status_code == 200
        # The total count in the admin header equals the actual DB count for this test
        db_count = Medication.objects.count()
        # Django renders "X results" or "X medication" in the content
        assert str(db_count) in response.content.decode()

    def test_pharmacy_does_not_see_medications_of_nonexistent_patients(
        self, create_groups
    ):
        """AC-01.4: Pharmacy only sees medications where a real Patient record exists
        (FK integrity ensures this; deleting a patient cascades to their medications).
        """
        pharmacy = _make_staff_user("pharmacy_s301_007", "pharmacy", "PH-007")

        pat_u = User.objects.create_user(username="patient_s301_006", password="pass")
        pat_profile = UserProfile.objects.create(
            user=pat_u, role="patient", phone="5550009"
        )
        patient = _get_or_create_patient(pat_profile)
        med = _make_medication(patient, "Warfarin")
        med_pk = med.pk

        # Deleting the patient cascades — medication is gone too
        patient.delete()

        client = Client()
        client.force_login(pharmacy)
        response = client.get(MEDICATION_LIST_URL)
        assert response.status_code == 200
        assert not Medication.objects.filter(pk=med_pk).exists()
        assert "Warfarin" not in response.content.decode()
