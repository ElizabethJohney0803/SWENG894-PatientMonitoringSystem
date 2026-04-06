"""
Tests for PBI-S3-12 — Nurse Appointment View (FR-N-1).

Test Cases: TC-S3-040, TC-S3-041, TC-S3-042

Acceptance Criteria:
  AC-12.1  A nurse user can view appointment records for patients assigned to them.
  AC-12.2  A nurse user sees zero appointments for patients not assigned to them.
  AC-12.3  Nurse's appointment view is read-only — no Save/Edit button shown,
           or POST returns 403.
"""

import pytest
from datetime import date, timedelta
from django.utils import timezone

from django.contrib.auth.models import User
from django.test import Client

from core.models import Appointment, Patient, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APPT_LIST_URL = "/admin/core/appointment/"
APPT_ADD_URL = "/admin/core/appointment/add/"


def _make_staff_user(username, role, license_number=None, phone="5550000"):
    user = User.objects.create_user(
        username=username, password="pass", is_staff=True, is_superuser=False
    )
    kw = {"user": user, "role": role, "phone": phone}
    if license_number:
        kw["license_number"] = license_number
    UserProfile.objects.create(**kw)
    return user


def _make_patient_record(profile, assigned_nurse=None, assigned_doctor=None):
    patient = Patient.objects.filter(user_profile=profile).first()
    if patient is None:
        patient = Patient(
            user_profile=profile,
            date_of_birth=date(1985, 4, 10),
            gender="F",
            address_line1="10 Nurse Ave",
            city="Clinicton",
            state="CS",
            postal_code="55555",
            phone_primary="5550007777",
        )
    if assigned_nurse:
        patient.assigned_nurse = assigned_nurse
    if assigned_doctor:
        patient.assigned_doctor = assigned_doctor
    patient.save()
    return patient


def _make_appointment(patient, doctor_profile, delta_days=3, status="scheduled"):
    dt = timezone.now() + timedelta(days=delta_days)
    return Appointment.objects.create(
        patient=patient,
        doctor=doctor_profile,
        appointment_datetime=dt,
        appointment_type="follow_up",
        status=status,
        location="Room 101",
    )


def _change_url(appt):
    return f"/admin/core/appointment/{appt.pk}/change/"


# ---------------------------------------------------------------------------
# TC-S3-040 — AC-12.1: Nurse can view appointments for assigned patients
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNurseSeesAssignedPatientAppointments:
    """TC-S3-040 — Nurse views appointment list and detail for their assigned patient."""

    def setup_method(self):
        self.nurse = _make_staff_user("nurse_s312a", "nurse", license_number="RN-S312A")
        self.doctor = _make_staff_user("doc_s312a", "doctor", license_number="MD-S312A")
        self.nurse_profile = UserProfile.objects.get(user=self.nurse)
        self.doc_profile = UserProfile.objects.get(user=self.doctor)

        pat_user = _make_staff_user("pat_s312a", "patient")
        pat_profile = UserProfile.objects.get(user=pat_user)
        self.patient = _make_patient_record(
            pat_profile,
            assigned_nurse=self.nurse_profile,
            assigned_doctor=self.doc_profile,
        )
        self.appt = _make_appointment(self.patient, self.doc_profile)

    def test_nurse_can_access_appointment_changelist(self):
        """TC-S3-040 (AC-12.1): Nurse GET changelist returns 200."""
        c = Client()
        c.login(username="nurse_s312a", password="pass")
        response = c.get(APPT_LIST_URL)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_nurse_sees_assigned_patient_appointment(self):
        """TC-S3-040 (AC-12.1): Nurse sees appointment for their assigned patient."""
        c = Client()
        c.login(username="nurse_s312a", password="pass")
        response = c.get(APPT_LIST_URL)
        assert response.status_code == 200
        assert (
            b"Room 101" in response.content
        ), "Nurse should see the appointment location for their assigned patient"

    def test_nurse_can_access_appointment_change_form(self):
        """TC-S3-040 (AC-12.1): Nurse GET change form for assigned patient's appointment returns 200."""
        c = Client()
        c.login(username="nurse_s312a", password="pass")
        response = c.get(_change_url(self.appt))
        assert response.status_code == 200

    def test_nurse_sees_appointment_status_in_changelist(self):
        """TC-S3-040 (AC-12.1): Appointment status column visible to nurse."""
        c = Client()
        c.login(username="nurse_s312a", password="pass")
        response = c.get(APPT_LIST_URL)
        assert response.status_code == 200
        # 'Scheduled' is the human-readable label for the status
        assert b"Scheduled" in response.content


# ---------------------------------------------------------------------------
# TC-S3-041 — AC-12.2: Nurse sees zero appointments for unassigned patients
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNurseCannotSeeUnassignedPatientAppointments:
    """TC-S3-041 — Nurse's queryset is scoped; unassigned patient appointments hidden."""

    def setup_method(self):
        self.nurse = _make_staff_user("nurse_s312b", "nurse", license_number="RN-S312B")
        self.other_nurse = _make_staff_user(
            "nurse_s312b2", "nurse", license_number="RN-S312B2"
        )
        self.doctor = _make_staff_user("doc_s312b", "doctor", license_number="MD-S312B")
        self.nurse_profile = UserProfile.objects.get(user=self.nurse)
        self.other_nurse_profile = UserProfile.objects.get(user=self.other_nurse)
        self.doc_profile = UserProfile.objects.get(user=self.doctor)

        # Patient assigned to OTHER nurse
        other_pat_user = _make_staff_user("pat_s312b_other", "patient")
        other_pat_profile = UserProfile.objects.get(user=other_pat_user)
        self.other_patient = _make_patient_record(
            other_pat_profile,
            assigned_nurse=self.other_nurse_profile,
            assigned_doctor=self.doc_profile,
        )
        self.other_appt = _make_appointment(self.other_patient, self.doc_profile)

    def test_nurse_changelist_is_empty_for_unassigned_appointments(self):
        """TC-S3-041 (AC-12.2): Nurse sees no appointments when none are assigned to them."""
        c = Client()
        c.login(username="nurse_s312b", password="pass")
        response = c.get(APPT_LIST_URL)
        assert response.status_code == 200
        # The appointment location for the other patient must not appear
        assert (
            b"Room 101" not in response.content
        ), "Nurse should not see appointments for unassigned patients"

    def test_nurse_cannot_access_unassigned_appointment_change_form(self):
        """TC-S3-041 (AC-12.2): Nurse GET on unassigned patient's appointment is denied."""
        c = Client()
        c.login(username="nurse_s312b", password="pass")
        response = c.get(_change_url(self.other_appt))
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for unassigned appointment, got {response.status_code}"

    def test_nurse_only_sees_own_assigned_appointments(self):
        """TC-S3-041 (AC-12.2): With both assigned and unassigned, nurse sees only own."""
        # Create a patient assigned to THIS nurse
        own_pat_user = _make_staff_user("pat_s312b_own", "patient")
        own_pat_profile = UserProfile.objects.get(user=own_pat_user)
        own_patient = _make_patient_record(
            own_pat_profile,
            assigned_nurse=self.nurse_profile,
            assigned_doctor=self.doc_profile,
        )
        own_appt = _make_appointment(own_patient, self.doc_profile)

        c = Client()
        c.login(username="nurse_s312b", password="pass")
        response = c.get(APPT_LIST_URL)
        assert response.status_code == 200
        content = response.content.decode()
        # own patient's appointment should appear
        assert "Room 101" in content
        # Unassigned patient's username should not appear in the list output
        assert (
            "pat_s312b_other" not in content
        ), "Unassigned patient should not appear in nurse's appointment list"


# ---------------------------------------------------------------------------
# TC-S3-042 — AC-12.3: Nurse view is entirely read-only
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNurseAppointmentViewIsReadOnly:
    """TC-S3-042 — Nurse has no add, change, or delete access."""

    def setup_method(self):
        self.nurse = _make_staff_user("nurse_s312c", "nurse", license_number="RN-S312C")
        self.doctor = _make_staff_user("doc_s312c", "doctor", license_number="MD-S312C")
        self.nurse_profile = UserProfile.objects.get(user=self.nurse)
        self.doc_profile = UserProfile.objects.get(user=self.doctor)

        pat_user = _make_staff_user("pat_s312c", "patient")
        pat_profile = UserProfile.objects.get(user=pat_user)
        self.patient = _make_patient_record(
            pat_profile,
            assigned_nurse=self.nurse_profile,
            assigned_doctor=self.doc_profile,
        )
        self.appt = _make_appointment(self.patient, self.doc_profile)

    def test_nurse_cannot_access_add_appointment_form(self):
        """TC-S3-042 (AC-12.3): Nurse GET add form is denied (302/403)."""
        c = Client()
        c.login(username="nurse_s312c", password="pass")
        response = c.get(APPT_ADD_URL)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for add form, got {response.status_code}"

    def test_nurse_post_to_add_is_denied(self):
        """TC-S3-042 (AC-12.3): Nurse POST to add appointment is denied."""
        c = Client()
        c.login(username="nurse_s312c", password="pass")
        response = c.post(APPT_ADD_URL, data={}, follow=False)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for POST add, got {response.status_code}"

    def test_nurse_post_to_change_form_is_denied(self):
        """TC-S3-042 (AC-12.3): Nurse POST to change form is denied (no change permission)."""
        c = Client()
        c.login(username="nurse_s312c", password="pass")
        payload = {
            "patient": self.patient.pk,
            "doctor": self.doc_profile.pk,
            "appointment_datetime": (timezone.now() + timedelta(days=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "appointment_type": "follow_up",
            "status": "confirmed",
            "location": "Room 999",
            "notes": "",
        }
        response = c.post(_change_url(self.appt), data=payload, follow=False)
        assert response.status_code in (
            302,
            403,
        ), f"Expected 302/403 for POST change, got {response.status_code}"

    def test_appointment_unchanged_after_nurse_post_attempt(self):
        """TC-S3-042 (AC-12.3): Location unchanged after nurse tries to edit."""
        original_location = self.appt.location
        c = Client()
        c.login(username="nurse_s312c", password="pass")
        payload = {
            "patient": self.patient.pk,
            "doctor": self.doc_profile.pk,
            "appointment_datetime": (timezone.now() + timedelta(days=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "appointment_type": "follow_up",
            "status": "confirmed",
            "location": "Room 999",
            "notes": "",
        }
        c.post(_change_url(self.appt), data=payload, follow=False)
        self.appt.refresh_from_db()
        assert (
            self.appt.location == original_location
        ), "Appointment location should not change after nurse POST attempt"

    def test_nurse_change_form_has_no_editable_inputs(self):
        """TC-S3-042 (AC-12.3): Change form for nurse shows no writable input for location."""
        c = Client()
        c.login(username="nurse_s312c", password="pass")
        response = c.get(_change_url(self.appt))
        assert response.status_code == 200
        content = response.content.decode()
        # location should NOT appear as a writable text input
        assert (
            'name="location"' not in content
        ), "location should be read-only (no editable input) for nurse"
