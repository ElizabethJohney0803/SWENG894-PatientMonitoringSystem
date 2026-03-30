"""
Unit tests for the Appointment model — PBI-S3-08.

Test Cases:
  TC-S3-021  Appointment model creation with all required fields
  TC-S3-022  Invalid status raises ValidationError
  TC-S3-023  Invalid appointment_type raises ValidationError
  TC-S3-024  __str__ returns human-readable patient name + date string
  TC-S3-025  Meta ordering and verbose names are correct
"""

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
)

import django

django.setup()

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from core.models import Appointment


def _make_future_dt(days=7):
    """Return a timezone-aware datetime `days` from now."""
    return timezone.now() + timedelta(days=days)


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAppointmentModelCreation:
    """TC-S3-021 — Appointment can be created with all required fields."""

    def test_appointment_creation_minimal(self, patient_user, doctor_user):
        """Create an Appointment with required fields; instance persists."""
        patient = patient_user.profile.patient_record
        doctor_profile = doctor_user.profile
        appt_dt = _make_future_dt()

        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_profile,
            appointment_datetime=appt_dt,
            appointment_type="initial_consultation",
            status="scheduled",
            location="Room 101",
        )

        appt.refresh_from_db()
        assert appt.pk is not None
        assert appt.patient == patient
        assert appt.doctor == doctor_profile
        assert appt.appointment_type == "initial_consultation"
        assert appt.status == "scheduled"
        assert appt.location == "Room 101"
        assert appt.notes == ""  # blank by default

    def test_appointment_default_status_is_scheduled(self, patient_user):
        """Status defaults to 'scheduled' when not provided."""
        patient = patient_user.profile.patient_record

        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="follow_up",
            location="Clinic A",
        )

        assert appt.status == "scheduled"

    def test_appointment_doctor_nullable(self, patient_user):
        """Appointment can be created without a doctor (doctor=None)."""
        patient = patient_user.profile.patient_record

        appt = Appointment.objects.create(
            patient=patient,
            doctor=None,
            appointment_datetime=_make_future_dt(),
            appointment_type="routine_checkup",
            location="Ward 3",
        )

        assert appt.doctor is None

    def test_appointment_notes_optional(self, patient_user, doctor_user):
        """Notes field is optional and defaults to empty string."""
        patient = patient_user.profile.patient_record

        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="lab_review",
            location="Lab B",
        )

        assert appt.notes == ""

    def test_appointment_all_status_choices_valid(self, patient_user):
        """All five status choices can be saved without error."""
        patient = patient_user.profile.patient_record
        valid_statuses = [
            "scheduled",
            "confirmed",
            "completed",
            "cancelled",
            "no_show",
        ]

        for status in valid_statuses:
            appt = Appointment(
                patient=patient,
                appointment_datetime=_make_future_dt(),
                appointment_type="follow_up",
                status=status,
                location="Room 1",
            )
            appt.clean()  # Must not raise

    def test_appointment_all_type_choices_valid(self, patient_user):
        """All five appointment_type choices can be saved without error."""
        patient = patient_user.profile.patient_record
        valid_types = [
            "initial_consultation",
            "follow_up",
            "routine_checkup",
            "lab_review",
            "urgent_care",
        ]

        for appt_type in valid_types:
            appt = Appointment(
                patient=patient,
                appointment_datetime=_make_future_dt(),
                appointment_type=appt_type,
                status="scheduled",
                location="Room 1",
            )
            appt.clean()  # Must not raise

    def test_appointment_timestamps_auto_populated(self, patient_user):
        """created_at and updated_at are auto-set on creation."""
        patient = patient_user.profile.patient_record

        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="urgent_care",
            location="ER",
        )

        assert appt.created_at is not None
        assert appt.updated_at is not None


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAppointmentStatusValidation:
    """TC-S3-022 — Invalid status raises ValidationError."""

    def test_invalid_status_raises_validation_error(self, patient_user):
        """clean() raises ValidationError when status is not a valid choice."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="follow_up",
            status="invalid_status",
            location="Room 1",
        )

        with pytest.raises(ValidationError) as exc_info:
            appt.clean()

        assert "status" in exc_info.value.message_dict

    def test_empty_string_status_raises_validation_error(self, patient_user):
        """clean() raises ValidationError when status is an empty string."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="follow_up",
            status="",
            location="Room 1",
        )

        with pytest.raises(ValidationError) as exc_info:
            appt.clean()

        assert "status" in exc_info.value.message_dict

    def test_misspelled_status_raises_validation_error(self, patient_user):
        """Misspelled but close status value is still rejected."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="follow_up",
            status="schedueld",  # typo
            location="Room 1",
        )

        with pytest.raises(ValidationError):
            appt.clean()


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAppointmentTypeValidation:
    """TC-S3-023 — Invalid appointment_type raises ValidationError."""

    def test_invalid_type_raises_validation_error(self, patient_user):
        """clean() raises ValidationError when appointment_type is invalid."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="mystery_visit",
            status="scheduled",
            location="Room 1",
        )

        with pytest.raises(ValidationError) as exc_info:
            appt.clean()

        assert "appointment_type" in exc_info.value.message_dict

    def test_empty_string_type_raises_validation_error(self, patient_user):
        """clean() raises ValidationError when appointment_type is empty."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="",
            status="scheduled",
            location="Room 1",
        )

        with pytest.raises(ValidationError) as exc_info:
            appt.clean()

        assert "appointment_type" in exc_info.value.message_dict

    def test_misspelled_type_raises_validation_error(self, patient_user):
        """Misspelled appointment_type value is rejected."""
        patient = patient_user.profile.patient_record

        appt = Appointment(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="folowup",  # typo
            status="scheduled",
            location="Room 1",
        )

        with pytest.raises(ValidationError):
            appt.clean()


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAppointmentStr:
    """TC-S3-024 — __str__ returns a human-readable patient name + date."""

    def test_str_contains_patient_full_name(self, patient_user, doctor_user):
        """__str__ includes the patient's full name."""
        patient = patient_user.profile.patient_record
        appt_dt = _make_future_dt()

        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user.profile,
            appointment_datetime=appt_dt,
            appointment_type="initial_consultation",
            status="scheduled",
            location="Room 101",
        )

        full_name = patient_user.get_full_name()
        assert full_name in str(appt)

    def test_str_contains_appointment_date(self, patient_user):
        """__str__ includes the appointment date in YYYY-MM-DD format."""
        patient = patient_user.profile.patient_record
        appt_dt = _make_future_dt()

        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=appt_dt,
            appointment_type="routine_checkup",
            location="Clinic B",
        )

        expected_date = appt_dt.strftime("%Y-%m-%d")
        assert expected_date in str(appt)

    def test_str_format_is_human_readable(self, patient_user):
        """__str__ returns a non-empty, descriptive string."""
        patient = patient_user.profile.patient_record

        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="lab_review",
            location="Lab A",
        )

        result = str(appt)
        assert isinstance(result, str)
        assert len(result) > 0
        # Must contain a separator between name and date
        assert " — " in result


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestAppointmentMeta:
    """TC-S3-025 — Meta class ordering and verbose names are correct."""

    def test_meta_ordering_by_appointment_datetime(self, patient_user):
        """Appointments are ordered ascending by appointment_datetime."""
        patient = patient_user.profile.patient_record
        now = timezone.now()

        appt_later = Appointment.objects.create(
            patient=patient,
            appointment_datetime=now + timedelta(days=10),
            appointment_type="follow_up",
            location="Room C",
        )
        appt_earlier = Appointment.objects.create(
            patient=patient,
            appointment_datetime=now + timedelta(days=3),
            appointment_type="follow_up",
            location="Room D",
        )

        appointments = list(
            Appointment.objects.filter(pk__in=[appt_later.pk, appt_earlier.pk])
        )
        assert appointments[0] == appt_earlier
        assert appointments[1] == appt_later

    def test_meta_verbose_name(self):
        """verbose_name is 'Appointment'."""
        assert Appointment._meta.verbose_name == "Appointment"

    def test_meta_verbose_name_plural(self):
        """verbose_name_plural is 'Appointments'."""
        assert Appointment._meta.verbose_name_plural == "Appointments"

    def test_appointment_cascade_delete_with_patient(self, patient_user):
        """Deleting the patient cascades and removes the appointment."""
        patient = patient_user.profile.patient_record
        appt = Appointment.objects.create(
            patient=patient,
            appointment_datetime=_make_future_dt(),
            appointment_type="urgent_care",
            location="ER",
        )
        appt_pk = appt.pk

        # Delete the entire patient user chain
        patient.delete()

        assert not Appointment.objects.filter(pk=appt_pk).exists()

    def test_appointment_doctor_set_null_on_delete(self, patient_user, doctor_user):
        """Deleting the doctor sets appointment.doctor to NULL."""
        patient = patient_user.profile.patient_record
        doctor_profile = doctor_user.profile

        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_profile,
            appointment_datetime=_make_future_dt(),
            appointment_type="follow_up",
            location="Room 5",
        )

        doctor_profile.delete()

        appt.refresh_from_db()
        assert appt.doctor is None
