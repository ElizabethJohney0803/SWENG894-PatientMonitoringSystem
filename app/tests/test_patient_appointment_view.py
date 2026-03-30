"""
Integration tests for the Patient Appointment View — PBI-S3-10.

Test Cases:
  TC-S3-026  Patient can view their own upcoming appointments (AC-10.1)
  TC-S3-027  Patient can view their own past appointments (AC-10.2)
  TC-S3-028  Patient sees zero appointments belonging to other patients (AC-10.3)
  TC-S3-029  Upcoming appointments are sorted ascending by appointment_datetime (AC-10.4)
  TC-S3-030  Detail view renders appointment date, time, doctor full name, location (AC-10.5)
  TC-S3-031  Patient appointment view is read-only — POST to change view returns 403 (AC-10.6)
"""

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
)

import django

django.setup()

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import Appointment, Patient, UserProfile


# ── helpers ────────────────────────────────────────────────────────────────


def _dt(delta_days):
    """Return a timezone-aware datetime offset from now by delta_days."""
    return timezone.now() + timedelta(days=delta_days)


def _make_appointment(patient, doctor=None, **kwargs):
    """Create and return a saved Appointment with sensible defaults."""
    defaults = {
        "appointment_datetime": _dt(7),
        "appointment_type": "follow_up",
        "status": "scheduled",
        "location": "Room 101",
    }
    defaults.update(kwargs)
    return Appointment.objects.create(patient=patient, doctor=doctor, **defaults)


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def patient_record(patient_user):
    """Ensure the patient has a Patient record and return it."""
    patient_user.profile.ensure_patient_record()
    return Patient.objects.get(user_profile=patient_user.profile)


@pytest.fixture
def patient_client(patient_user):
    """Django test client logged in as the patient user."""
    client = Client()
    client.force_login(patient_user)
    return client, patient_user


@pytest.fixture
def other_patient_record(create_groups):
    """A second patient with their own Patient record."""
    from django.contrib.auth.models import User

    user = User.objects.create_user(
        username="other_patient",
        first_name="Other",
        last_name="Patient",
        password="testpass123",
    )
    profile = UserProfile.objects.create(user=user, role="patient")
    profile.ensure_patient_record()
    return Patient.objects.get(user_profile=profile)


# ── TC-S3-026 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientViewsOwnUpcomingAppointments:
    """TC-S3-026 — AC-10.1: Patient can view their own upcoming appointments."""

    def test_patient_changelist_accessible(self, patient_client, patient_record):
        """Patient changelist returns HTTP 200."""
        client, _ = patient_client
        _make_appointment(patient_record, status="scheduled")

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)
        assert response.status_code == 200

    def test_patient_sees_own_upcoming_appointment(
        self, patient_client, patient_record, doctor_user
    ):
        """Patient's own future/scheduled appointment appears in the changelist."""
        client, _ = patient_client
        appt = _make_appointment(
            patient_record,
            doctor=doctor_user.profile,
            status="scheduled",
            appointment_datetime=_dt(5),
        )

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)

        assert response.status_code == 200
        # The appointment datetime should appear in the response
        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert (
            appt.pk in pks
        ), "Patient's upcoming appointment not in changelist queryset"

    def test_patient_upcoming_filter_returns_future_appointments(
        self, patient_client, patient_record
    ):
        """Using the time=upcoming filter returns future non-completed appointments."""
        client, _ = patient_client
        future_appt = _make_appointment(
            patient_record, status="scheduled", appointment_datetime=_dt(10)
        )
        past_appt = _make_appointment(
            patient_record, status="completed", appointment_datetime=_dt(-5)
        )

        url = reverse("admin:core_appointment_changelist") + "?time=upcoming"
        response = client.get(url)

        assert response.status_code == 200
        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert future_appt.pk in pks
        assert past_appt.pk not in pks


# ── TC-S3-027 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientViewsOwnPastAppointments:
    """TC-S3-027 — AC-10.2: Patient can view their own past appointments."""

    def test_patient_sees_own_past_appointment(self, patient_client, patient_record):
        """Patient's own past/completed appointment is accessible."""
        client, _ = patient_client
        past_appt = _make_appointment(
            patient_record,
            status="completed",
            appointment_datetime=_dt(-10),
        )

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)

        assert response.status_code == 200
        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert (
            past_appt.pk in pks
        ), "Patient's past appointment not in changelist queryset"

    def test_patient_past_filter_returns_past_appointments(
        self, patient_client, patient_record
    ):
        """Using the time=past filter returns past/completed appointments."""
        client, _ = patient_client
        future_appt = _make_appointment(
            patient_record, status="scheduled", appointment_datetime=_dt(10)
        )
        past_appt = _make_appointment(
            patient_record, status="completed", appointment_datetime=_dt(-5)
        )

        url = reverse("admin:core_appointment_changelist") + "?time=past"
        response = client.get(url)

        assert response.status_code == 200
        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert past_appt.pk in pks
        assert future_appt.pk not in pks


# ── TC-S3-028 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientCannotSeeOtherPatientsAppointments:
    """TC-S3-028 — AC-10.3: Patient sees zero appointments from other patients."""

    def test_other_patient_appointments_excluded(
        self, patient_client, patient_record, other_patient_record
    ):
        """Another patient's appointment does NOT appear in the queryset."""
        client, _ = patient_client

        # Create appointments for BOTH patients
        own_appt = _make_appointment(patient_record, status="scheduled")
        other_appt = _make_appointment(other_patient_record, status="scheduled")

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)

        assert response.status_code == 200
        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert own_appt.pk in pks
        assert (
            other_appt.pk not in pks
        ), "Other patient's appointment should NOT appear in the patient's queryset"

    def test_queryset_count_matches_own_appointments_only(
        self, patient_client, patient_record, other_patient_record
    ):
        """Queryset count equals exactly the logged-in patient's own appointments."""
        client, _ = patient_client

        _make_appointment(patient_record, status="scheduled")
        _make_appointment(patient_record, status="confirmed")
        _make_appointment(other_patient_record, status="scheduled")

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)

        cl = response.context["cl"]
        assert (
            cl.queryset.count() == 2
        ), f"Expected 2 own appointments, got {cl.queryset.count()}"


# ── TC-S3-029 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientAppointmentOrdering:
    """TC-S3-029 — AC-10.4: Upcoming appointments sorted ascending by datetime."""

    def test_appointments_ordered_ascending(self, patient_client, patient_record):
        """Appointments in the queryset are ordered earliest-first."""
        client, _ = patient_client

        # Create out-of-order appointments
        appt_third = _make_appointment(
            patient_record, status="scheduled", appointment_datetime=_dt(15)
        )
        appt_first = _make_appointment(
            patient_record, status="scheduled", appointment_datetime=_dt(3)
        )
        appt_second = _make_appointment(
            patient_record, status="scheduled", appointment_datetime=_dt(8)
        )

        url = reverse("admin:core_appointment_changelist")
        response = client.get(url)

        cl = response.context["cl"]
        pks = list(cl.queryset.values_list("pk", flat=True))
        assert pks == [appt_first.pk, appt_second.pk, appt_third.pk], (
            f"Expected ascending order [{appt_first.pk}, {appt_second.pk}, "
            f"{appt_third.pk}], got {pks}"
        )


# ── TC-S3-030 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientAppointmentDetailView:
    """TC-S3-030 — AC-10.5: Detail view renders date, time, doctor full name, location."""

    def test_detail_view_accessible(self, patient_client, patient_record, doctor_user):
        """Patient can access the detail (change) view for their own appointment."""
        client, _ = patient_client
        appt = _make_appointment(
            patient_record,
            doctor=doctor_user.profile,
            location="Clinic A",
        )

        url = reverse("admin:core_appointment_change", args=[appt.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_view_shows_doctor_full_name(
        self, patient_client, patient_record, doctor_user
    ):
        """AC-10.5: Doctor's full name appears in the appointment detail view."""
        client, _ = patient_client
        appt = _make_appointment(
            patient_record, doctor=doctor_user.profile, location="Clinic B"
        )

        url = reverse("admin:core_appointment_change", args=[appt.pk])
        response = client.get(url)

        assert response.status_code == 200
        doctor_full_name = doctor_user.get_full_name()
        assert (
            doctor_full_name.encode() in response.content
        ), f"Doctor full name '{doctor_full_name}' not found in detail view."

    def test_detail_view_shows_location(
        self, patient_client, patient_record, doctor_user
    ):
        """AC-10.5: Location appears in the appointment detail view."""
        client, _ = patient_client
        appt = _make_appointment(
            patient_record,
            doctor=doctor_user.profile,
            location="Ward 3 - Room 12",
        )

        url = reverse("admin:core_appointment_change", args=[appt.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert (
            b"Ward 3 - Room 12" in response.content
        ), "Location not found in appointment detail view."

    def test_detail_view_shows_appointment_datetime(
        self, patient_client, patient_record
    ):
        """AC-10.5: Appointment date and time appear in the detail view."""
        client, _ = patient_client
        appt_dt = _dt(7)
        appt = _make_appointment(
            patient_record,
            appointment_datetime=appt_dt,
            location="Room 5",
        )

        url = reverse("admin:core_appointment_change", args=[appt.pk])
        response = client.get(url)

        assert response.status_code == 200
        # The date portion of the datetime should appear in the page
        date_str = appt_dt.strftime("%Y-%m-%d").encode()
        assert (
            date_str in response.content
        ), f"Appointment date '{date_str.decode()}' not found in detail view."

    def test_patient_cannot_access_other_patients_detail(
        self, patient_client, other_patient_record
    ):
        """Patient cannot view the detail page for another patient's appointment."""
        client, _ = patient_client
        other_appt = _make_appointment(other_patient_record, location="Secret Room")

        url = reverse("admin:core_appointment_change", args=[other_appt.pk])
        response = client.get(url)

        # Django admin redirects to admin index (302) when the object is not in
        # the filtered queryset — equivalent to "not found" for this user.
        assert response.status_code in (302, 403), (
            f"Expected 302 or 403 when patient accesses another patient's appointment, "
            f"got {response.status_code}"
        )


# ── TC-S3-031 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientAppointmentViewIsReadOnly:
    """TC-S3-031 — AC-10.6: Patient appointment view is read-only."""

    def test_patient_has_no_add_permission(self, patient_client, patient_record):
        """Patient cannot add a new appointment — add URL returns 403."""
        client, _ = patient_client
        url = reverse("admin:core_appointment_add")
        response = client.get(url)
        assert (
            response.status_code == 403
        ), f"Expected 403 for patient on add appointment, got {response.status_code}"

    def test_patient_post_to_change_view_returns_403(
        self, patient_client, patient_record, doctor_user
    ):
        """AC-10.6: POST to own appointment's change view is denied (403)."""
        client, _ = patient_client
        appt = _make_appointment(
            patient_record, doctor=doctor_user.profile, status="scheduled"
        )

        url = reverse("admin:core_appointment_change", args=[appt.pk])
        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_user.profile.pk,
            "appointment_datetime_0": appt.appointment_datetime.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt.appointment_datetime.strftime("%H:%M:%S"),
            "appointment_type": appt.appointment_type,
            "status": "cancelled",  # attempt to change status
            "location": appt.location,
            "notes": appt.notes,
        }
        response = client.post(url, data=post_data)
        assert (
            response.status_code == 403
        ), f"Expected 403 when patient POSTs to change view, got {response.status_code}"

        # Verify the status was NOT changed
        appt.refresh_from_db()
        assert (
            appt.status == "scheduled"
        ), "Appointment status must not change when patient attempts a POST"

    def test_patient_has_no_delete_permission(self, patient_client, patient_record):
        """Patient cannot delete their own appointment."""
        client, _ = patient_client
        appt = _make_appointment(patient_record, status="scheduled")

        delete_url = reverse("admin:core_appointment_delete", args=[appt.pk])
        response = client.post(delete_url, data={"post": "yes"})
        assert response.status_code == 403, (
            f"Expected 403 when patient tries to delete appointment, "
            f"got {response.status_code}"
        )

        # Record should still exist
        assert Appointment.objects.filter(
            pk=appt.pk
        ).exists(), "Appointment should not have been deleted by a patient."
