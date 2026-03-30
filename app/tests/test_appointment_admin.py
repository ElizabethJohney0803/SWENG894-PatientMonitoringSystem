"""
Integration tests for the Admin Appointment Scheduling Interface — PBI-S3-09.

Test Cases:
  TC-S3-032  Admin can create a new appointment; save redirects to changelist (HTTP 302)
  TC-S3-033  Admin can edit an existing appointment and persist changes
  TC-S3-034  Admin can delete an appointment record
  TC-S3-035  Appointment changelist includes a sidebar filter for status
  TC-S3-036  Changelist displays required columns: patient name, doctor name,
             appointment date/time, type, and status
"""

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
)

import django

django.setup()

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.admin import AppointmentAdmin
from core.models import Appointment, Patient, UserProfile


# ── helpers ────────────────────────────────────────────────────────────────


def _future_dt(days=7):
    """Return a timezone-aware datetime `days` from now."""
    return timezone.now() + timedelta(days=days)


def _make_appointment(patient, doctor=None, **kwargs):
    """Create and return a saved Appointment."""
    defaults = {
        "appointment_datetime": _future_dt(),
        "appointment_type": "follow_up",
        "status": "scheduled",
        "location": "Room 101",
    }
    defaults.update(kwargs)
    return Appointment.objects.create(patient=patient, doctor=doctor, **defaults)


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(admin_user):
    """Django test client logged in as the admin user."""
    client = Client()
    client.force_login(admin_user)
    return client, admin_user


@pytest.fixture
def patient_record(patient_user):
    """Ensure the patient has a Patient record and return it."""
    patient_user.profile.ensure_patient_record()
    return Patient.objects.get(user_profile=patient_user.profile)


# ── TC-S3-032 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminCreateAppointment:
    """TC-S3-032 — Admin can create a new appointment; save redirects to changelist."""

    def test_create_appointment_redirects_to_changelist(
        self, admin_client, patient_record, doctor_user
    ):
        """
        AC-09.1: POST to add-appointment page with valid data results in HTTP 302
        redirect to the appointment changelist.
        """
        client, _ = admin_client
        doctor_profile = doctor_user.profile
        appt_dt = _future_dt(days=14)

        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_profile.pk,
            "appointment_datetime_0": appt_dt.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt_dt.strftime("%H:%M:%S"),
            "appointment_type": "initial_consultation",
            "status": "scheduled",
            "location": "Clinic A",
            "notes": "",
        }

        add_url = reverse("admin:core_appointment_add")
        response = client.post(add_url, data=post_data)

        # Should redirect (302) to changelist after save
        assert response.status_code == 302, (
            f"Expected 302 redirect after create, got {response.status_code}. "
            f"Form errors: {getattr(response, 'context', {})}"
        )
        # The redirect target should be the changelist URL
        changelist_url = reverse("admin:core_appointment_changelist")
        assert changelist_url in response["Location"], (
            f"Expected redirect to changelist {changelist_url}, "
            f"got {response['Location']}"
        )

    def test_appointment_persisted_after_create(
        self, admin_client, patient_record, doctor_user
    ):
        """Created appointment is persisted in the database."""
        client, _ = admin_client
        doctor_profile = doctor_user.profile
        appt_dt = _future_dt(days=10)

        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_profile.pk,
            "appointment_datetime_0": appt_dt.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt_dt.strftime("%H:%M:%S"),
            "appointment_type": "routine_checkup",
            "status": "confirmed",
            "location": "Ward 2",
            "notes": "Initial checkup notes",
        }

        add_url = reverse("admin:core_appointment_add")
        client.post(add_url, data=post_data)

        assert Appointment.objects.filter(
            patient=patient_record,
            appointment_type="routine_checkup",
            status="confirmed",
            location="Ward 2",
        ).exists(), "Appointment was not saved to the database."


# ── TC-S3-033 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminEditAppointment:
    """TC-S3-033 — Admin can edit an existing appointment and persist changes."""

    def test_edit_appointment_status(self, admin_client, patient_record, doctor_user):
        """
        AC-09.2: Admin edits status of an appointment; change persists.
        """
        client, _ = admin_client
        appt = _make_appointment(
            patient_record, doctor=doctor_user.profile, status="scheduled"
        )

        change_url = reverse("admin:core_appointment_change", args=[appt.pk])
        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_user.profile.pk,
            "appointment_datetime_0": appt.appointment_datetime.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt.appointment_datetime.strftime("%H:%M:%S"),
            "appointment_type": appt.appointment_type,
            "status": "confirmed",  # changed
            "location": appt.location,
            "notes": appt.notes,
        }

        response = client.post(change_url, data=post_data)
        assert (
            response.status_code == 302
        ), f"Expected 302 after edit, got {response.status_code}"

        appt.refresh_from_db()
        assert appt.status == "confirmed", f"Status not updated, still '{appt.status}'"

    def test_edit_appointment_notes(self, admin_client, patient_record, doctor_user):
        """AC-09.2: Admin edits notes; change persists."""
        client, _ = admin_client
        appt = _make_appointment(patient_record, doctor=doctor_user.profile, notes="")

        change_url = reverse("admin:core_appointment_change", args=[appt.pk])
        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_user.profile.pk,
            "appointment_datetime_0": appt.appointment_datetime.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt.appointment_datetime.strftime("%H:%M:%S"),
            "appointment_type": appt.appointment_type,
            "status": appt.status,
            "location": appt.location,
            "notes": "Follow up on lab results",  # changed
        }

        client.post(change_url, data=post_data)
        appt.refresh_from_db()
        assert appt.notes == "Follow up on lab results"

    def test_edit_appointment_location(self, admin_client, patient_record, doctor_user):
        """AC-09.2: Admin edits location; change persists."""
        client, _ = admin_client
        appt = _make_appointment(
            patient_record, doctor=doctor_user.profile, location="Room 101"
        )

        change_url = reverse("admin:core_appointment_change", args=[appt.pk])
        post_data = {
            "patient": patient_record.pk,
            "doctor": doctor_user.profile.pk,
            "appointment_datetime_0": appt.appointment_datetime.strftime("%Y-%m-%d"),
            "appointment_datetime_1": appt.appointment_datetime.strftime("%H:%M:%S"),
            "appointment_type": appt.appointment_type,
            "status": appt.status,
            "location": "Clinic B",  # changed
            "notes": appt.notes,
        }

        client.post(change_url, data=post_data)
        appt.refresh_from_db()
        assert appt.location == "Clinic B"


# ── TC-S3-034 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminDeleteAppointment:
    """TC-S3-034 — Admin can delete an appointment record."""

    def test_delete_appointment(self, admin_client, patient_record, doctor_user):
        """
        AC-09.3: Admin deletes an appointment; record is removed from the database.
        """
        client, _ = admin_client
        appt = _make_appointment(patient_record, doctor=doctor_user.profile)
        appt_pk = appt.pk

        delete_url = reverse("admin:core_appointment_delete", args=[appt_pk])
        # Django admin delete requires a POST with confirmation
        response = client.post(delete_url, data={"post": "yes"})

        assert (
            response.status_code == 302
        ), f"Expected 302 after delete, got {response.status_code}"
        assert not Appointment.objects.filter(
            pk=appt_pk
        ).exists(), "Appointment was not deleted from the database."


# ── TC-S3-035 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestAppointmentChangelistStatusFilter:
    """TC-S3-035 — Appointment changelist includes a sidebar filter for status."""

    def test_status_filter_present_in_list_filter(self):
        """
        AC-09.4: AppointmentAdmin.list_filter includes 'status'.
        """
        site = AdminSite()
        appt_admin = AppointmentAdmin(Appointment, site)
        assert (
            "status" in appt_admin.list_filter
        ), "AppointmentAdmin.list_filter must include 'status'"

    def test_changelist_renders_with_status_filter(
        self, admin_client, patient_record, doctor_user
    ):
        """
        AC-09.4: Changelist page renders with status filter applied (HTTP 200),
        and the queryset is correctly narrowed to the selected status.
        """
        client, _ = admin_client
        _make_appointment(
            patient_record, doctor=doctor_user.profile, status="scheduled"
        )
        _make_appointment(
            patient_record, doctor=doctor_user.profile, status="confirmed"
        )

        changelist_url = reverse("admin:core_appointment_changelist")
        # Filter to scheduled appointments only
        response = client.get(changelist_url + "?status=scheduled")

        assert (
            response.status_code == 200
        ), f"Changelist with status filter returned {response.status_code}"
        # The filtered queryset in context should contain exactly 1 result
        cl = response.context["cl"]
        assert cl.queryset.count() == 1, (
            f"Expected 1 appointment after status=scheduled filter, "
            f"got {cl.queryset.count()}"
        )
        assert cl.queryset.first().status == "scheduled"

    def test_date_hierarchy_attribute_set(self):
        """
        date_hierarchy must be set to 'appointment_datetime' on AppointmentAdmin.
        """
        site = AdminSite()
        appt_admin = AppointmentAdmin(Appointment, site)
        assert (
            appt_admin.date_hierarchy == "appointment_datetime"
        ), "AppointmentAdmin.date_hierarchy must be 'appointment_datetime'"


# ── TC-S3-036 ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestAppointmentChangelistColumns:
    """TC-S3-036 — Changelist displays required columns."""

    def test_list_display_contains_required_columns(self):
        """
        AC-09.5: list_display includes patient name, doctor name, appointment
        date/time, type, and status columns.
        """
        site = AdminSite()
        appt_admin = AppointmentAdmin(Appointment, site)

        assert (
            "get_patient_name" in appt_admin.list_display
        ), "list_display must include patient name column ('get_patient_name')"
        assert (
            "get_doctor_name" in appt_admin.list_display
        ), "list_display must include doctor name column ('get_doctor_name')"
        assert (
            "appointment_datetime" in appt_admin.list_display
        ), "list_display must include 'appointment_datetime'"
        assert (
            "appointment_type" in appt_admin.list_display
        ), "list_display must include 'appointment_type'"
        assert "status" in appt_admin.list_display, "list_display must include 'status'"

    def test_changelist_renders_patient_name(
        self, admin_client, patient_record, doctor_user
    ):
        """
        AC-09.5: Changelist page content includes the patient's full name.
        """
        client, _ = admin_client
        _make_appointment(patient_record, doctor=doctor_user.profile)

        changelist_url = reverse("admin:core_appointment_changelist")
        response = client.get(changelist_url)

        assert response.status_code == 200
        patient_full_name = patient_record.user_profile.user.get_full_name()
        assert (
            patient_full_name.encode() in response.content
        ), f"Patient name '{patient_full_name}' not found in changelist response."

    def test_changelist_renders_doctor_name(
        self, admin_client, patient_record, doctor_user
    ):
        """
        AC-09.5: Changelist page content includes the doctor's full name.
        """
        client, _ = admin_client
        _make_appointment(patient_record, doctor=doctor_user.profile)

        changelist_url = reverse("admin:core_appointment_changelist")
        response = client.get(changelist_url)

        assert response.status_code == 200
        doctor_full_name = doctor_user.get_full_name()
        assert (
            doctor_full_name.encode() in response.content
        ), f"Doctor name '{doctor_full_name}' not found in changelist response."

    def test_changelist_renders_status(self, admin_client, patient_record, doctor_user):
        """
        AC-09.5: Changelist page content includes the appointment status.
        """
        client, _ = admin_client
        _make_appointment(
            patient_record, doctor=doctor_user.profile, status="confirmed"
        )

        changelist_url = reverse("admin:core_appointment_changelist")
        response = client.get(changelist_url)

        assert response.status_code == 200
        # "Confirmed" is the human-readable form of "confirmed"
        assert (
            b"Confirmed" in response.content
        ), "Status 'Confirmed' not found in changelist response."
