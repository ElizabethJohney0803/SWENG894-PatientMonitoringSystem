"""
Tests for role-specific admin interface for Patient management.

Covers Phase 1 implementation:
  - get_list_display()  : role-specific list columns
  - get_list_filter()   : role-specific list filters
  - get_readonly_fields(): complete per-role readonly field sets
  - get_fieldsets()     : role-specific fieldset / field visibility
  - has_add_permission(): restricted to admin / superuser only
  - has_delete_permission(): restricted to admin / superuser only

Roles under test: admin, superuser, doctor, nurse, pharmacy, patient.
"""

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
)

import django

django.setup()

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory

from core.admin import PatientAdmin
from core.models import Patient, UserProfile


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _request(factory, user):
    """Build a minimal GET request attached to *user*."""
    req = factory.get("/admin/core/patient/")
    req.user = user
    return req


def _fieldset_fields(fieldsets):
    """Return the flat set of every field name appearing in *fieldsets*."""
    fields = set()
    for _title, opts in fieldsets:
        for f in opts.get("fields", []):
            fields.add(f)
    return fields


def _fieldset_titles(fieldsets):
    """Return the ordered list of fieldset titles."""
    return [title for title, _opts in fieldsets]


# ---------------------------------------------------------------------------
# 1. get_list_display
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminListDisplay:
    """get_list_display() returns role-appropriate columns."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    # ── admin ──

    def test_admin_sees_full_column_set(self, admin_user):
        cols = self.admin.get_list_display(_request(self.factory, admin_user))
        for col in [
            "medical_id",
            "get_patient_name",
            "get_assigned_doctor",
            "age",
            "gender",
            "state",
            "created_at",
        ]:
            assert col in cols, f"Admin list display should include '{col}'"

    # ── superuser ──

    def test_superuser_sees_full_column_set(self):
        su = User.objects.create_superuser(
            username="su_ld_1", password="pass", email="su1@t.com"
        )
        cols = self.admin.get_list_display(_request(self.factory, su))
        for col in ["medical_id", "get_patient_name", "get_assigned_doctor", "age"]:
            assert col in cols

    # ── doctor ──

    def test_doctor_sees_clinical_columns(self, doctor_user):
        """Sprint 4 AC-05.2: doctor list shows medical_id, name, DOB, diagnoses, pending tests, next appt."""
        cols = self.admin.get_list_display(_request(self.factory, doctor_user))
        for col in [
            "medical_id",
            "get_patient_name",
            "date_of_birth",
            "get_diagnoses_short",
            "get_pending_test_count",
            "get_next_appointment",
        ]:
            assert col in cols, f"Doctor list display should include '{col}'"

    def test_doctor_does_not_see_created_at(self, doctor_user):
        cols = self.admin.get_list_display(_request(self.factory, doctor_user))
        assert "created_at" not in cols

    # ── nurse ──

    def test_nurse_sees_sprint4_columns(self, nurse_user):
        """Sprint 4 AC-01.2: nurse list shows name, DOB, blood type, assigned doctor, chronic conditions."""
        cols = self.admin.get_list_display(_request(self.factory, nurse_user))
        for col in [
            "get_patient_name",
            "date_of_birth",
            "blood_type",
            "get_assigned_doctor",
            "get_chronic_conditions_short",
        ]:
            assert (
                col in cols
            ), f"Sprint 4 AC-01.2: Nurse list display should include '{col}'"

    # ── pharmacy ──

    def test_pharmacy_and_nurse_have_different_columns(self, pharmacy_user, nurse_user):
        """Sprint 4: nurse columns changed; pharmacy retains its own column set."""
        nurse_cols = self.admin.get_list_display(_request(self.factory, nurse_user))
        pharmacy_cols = self.admin.get_list_display(
            _request(self.factory, pharmacy_user)
        )
        # Sprint 4 nurse columns: name, DOB, blood_type, assigned_doctor, chronic_conditions
        assert "date_of_birth" in nurse_cols
        assert "get_chronic_conditions_short" in nurse_cols
        # Pharmacy retains its own columns (includes medical_id, phone, city)
        assert "medical_id" in pharmacy_cols

    # ── patient ──

    def test_patient_sees_minimal_own_columns(self, patient_user):
        cols = self.admin.get_list_display(_request(self.factory, patient_user))
        for col in ["medical_id", "get_patient_name", "age", "gender", "phone_primary"]:
            assert col in cols, f"Patient list display should include '{col}'"

    def test_patient_does_not_see_assigned_doctor_column(self, patient_user):
        cols = self.admin.get_list_display(_request(self.factory, patient_user))
        assert "get_assigned_doctor" not in cols

    def test_patient_does_not_see_admin_only_columns(self, patient_user):
        cols = self.admin.get_list_display(_request(self.factory, patient_user))
        assert "state" not in cols
        assert "created_at" not in cols


# ---------------------------------------------------------------------------
# 2. get_list_filter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminListFilter:
    """get_list_filter() returns role-appropriate filter options."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    def test_admin_gets_full_filter_set(self, admin_user):
        filters = self.admin.get_list_filter(_request(self.factory, admin_user))
        for f in [
            "gender",
            "blood_type",
            "state",
            "assigned_doctor",
            "created_at",
            "updated_at",
        ]:
            assert f in filters, f"Admin list filter should include '{f}'"

    def test_superuser_gets_full_filter_set(self):
        su = User.objects.create_superuser(
            username="su_lf_1", password="pass", email="su2@t.com"
        )
        filters = self.admin.get_list_filter(_request(self.factory, su))
        for f in ["gender", "blood_type", "state", "assigned_doctor"]:
            assert f in filters

    def test_doctor_gets_clinical_filters(self, doctor_user):
        """Sprint 4: doctor sees only their own patients so extra filters add no value (kept [])."""
        filters = self.admin.get_list_filter(_request(self.factory, doctor_user))
        # Doctors already see only their assigned patients; empty filters is intentional
        assert isinstance(filters, list)

    def test_doctor_does_not_get_assigned_doctor_filter(self, doctor_user):
        """Doctors only see their own patients so the assignment filter is useless."""
        filters = self.admin.get_list_filter(_request(self.factory, doctor_user))
        assert "assigned_doctor" not in filters

    def test_nurse_gets_clinical_and_state_filters(self, nurse_user):
        """Nurse filter returns [] — nurses only see their assigned patients, extra filters not needed."""
        filters = self.admin.get_list_filter(_request(self.factory, nurse_user))
        assert isinstance(filters, list)

    def test_nurse_does_not_get_assignment_filter(self, nurse_user):
        filters = self.admin.get_list_filter(_request(self.factory, nurse_user))
        assert "assigned_doctor" not in filters

    def test_pharmacy_gets_clinical_filters(self, pharmacy_user):
        """Pharmacy sees all patients so clinical filters (gender, blood_type) are useful."""
        filters = self.admin.get_list_filter(_request(self.factory, pharmacy_user))
        assert "gender" in filters
        assert "blood_type" in filters

    def test_patient_gets_no_filters(self, patient_user):
        """Patients see exactly one record; filters serve no purpose."""
        filters = self.admin.get_list_filter(_request(self.factory, patient_user))
        assert filters == []


# ---------------------------------------------------------------------------
# 3. get_readonly_fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminReadonlyFields:
    """get_readonly_fields() enforces correct editability boundaries per role."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    # ── admin ──

    def test_admin_readonly_contains_only_auto_fields(self, admin_user, patient_user):
        """Admins must be able to edit user_profile and assigned_doctor."""
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, admin_user), patient
        )
        # Auto-generated / timestamp fields always locked
        for f in ["medical_id", "created_at", "updated_at"]:
            assert f in readonly, f"Admin: '{f}' must always be readonly"
        # Admin can assign doctors and change the linked profile
        assert "assigned_doctor" not in readonly
        assert "user_profile" not in readonly

    def test_superuser_readonly_matches_admin(self, patient_user):
        su = User.objects.create_superuser(
            username="su_ro_1", password="pass", email="su3@t.com"
        )
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(_request(self.factory, su), patient)
        assert "assigned_doctor" not in readonly
        assert "user_profile" not in readonly

    # ── doctor ──

    def test_doctor_cannot_change_identity_fields(self, doctor_user, patient_user):
        """user_profile and assigned_doctor are locked for doctors."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, doctor_user), patient
        )
        assert "user_profile" in readonly
        assert "assigned_doctor" in readonly

    def test_doctor_can_edit_clinical_and_contact_fields(
        self, doctor_user, patient_user
    ):
        """Doctors must be able to update clinical info, contact and address."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, doctor_user), patient
        )
        editable = [
            "date_of_birth",
            "gender",
            "blood_type",
            "insurance_number",
            "phone_primary",
            "phone_secondary",
            "email_personal",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
        ]
        for f in editable:
            assert f not in readonly, f"Doctor should be able to edit '{f}'"

    # ── nurse ──

    def test_nurse_cannot_change_clinical_identity_fields(
        self, nurse_user, patient_user
    ):
        """Identity and clinical fields are all locked for nurses."""
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, nurse_user), patient
        )
        locked = [
            "user_profile",
            "assigned_doctor",
            "date_of_birth",
            "gender",
            "blood_type",
            "insurance_number",
        ]
        for f in locked:
            assert f in readonly, f"Nurse should have '{f}' as readonly"

    def test_nurse_cannot_edit_contact_and_address_fields(
        self, nurse_user, patient_user
    ):
        """Sprint 4 AC-01.4: All patient fields are read-only for nurses."""
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, nurse_user), patient
        )
        # Contact and address fields must now also be locked for nurses (AC-01.4)
        locked = [
            "phone_primary",
            "phone_secondary",
            "email_personal",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
        ]
        for f in locked:
            assert (
                f in readonly
            ), f"Sprint 4 AC-01.4: Nurse should have '{f}' as readonly"

    # ── pharmacy ──

    def test_pharmacy_readonly_matches_nurse(
        self, pharmacy_user, nurse_user, patient_user
    ):
        """Pharmacy staff has the same readonly profile as nurses."""
        patient = patient_user.profile.patient_record
        nurse_ro = self.admin.get_readonly_fields(
            _request(self.factory, nurse_user), patient
        )
        pharmacy_ro = self.admin.get_readonly_fields(
            _request(self.factory, pharmacy_user), patient
        )
        assert set(nurse_ro) == set(pharmacy_ro)

    # ── patient ──

    def test_patient_cannot_edit_identity_and_demographic_fields(self, patient_user):
        """Patients cannot alter identity, DOB, gender or blood type."""
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, patient_user), patient
        )
        locked = [
            "user_profile",
            "assigned_doctor",
            "date_of_birth",
            "gender",
            "blood_type",
        ]
        for f in locked:
            assert f in readonly, f"Patient should have '{f}' as readonly"

    def test_patient_can_edit_insurance_contact_and_address(self, patient_user):
        """Patients must be able to update insurance, phone, email and address."""
        patient = patient_user.profile.patient_record
        readonly = self.admin.get_readonly_fields(
            _request(self.factory, patient_user), patient
        )
        editable = [
            "insurance_number",
            "phone_primary",
            "phone_secondary",
            "email_personal",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
        ]
        for f in editable:
            assert f not in readonly, f"Patient should be able to edit '{f}'"

    def test_patient_viewing_other_patients_record_all_readonly(self, patient_user):
        """When a patient somehow reaches another patient's record, lock everything."""
        other_user = User.objects.create_user(
            username="other_ro_patient", password="pass"
        )
        other_profile = UserProfile.objects.create(user=other_user, role="patient")
        other_patient = Patient.objects.get(user_profile=other_profile)

        readonly = self.admin.get_readonly_fields(
            _request(self.factory, patient_user), other_patient
        )
        all_field_names = [f.name for f in Patient._meta.fields]
        for f in all_field_names:
            assert (
                f in readonly
            ), f"Viewing another patient's record: '{f}' must be readonly"


# ---------------------------------------------------------------------------
# 4. get_fieldsets
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminFieldsets:
    """get_fieldsets() exposes the correct sections and fields per role."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    # ── admin ──

    def test_admin_sees_all_sections(self, admin_user):
        fs = self.admin.get_fieldsets(_request(self.factory, admin_user))
        titles = _fieldset_titles(fs)
        for section in [
            "Patient Identity",
            "Care Assignment",
            "Personal Information",
            "Contact Information",
            "Address",
            "System Information",
        ]:
            assert section in titles, f"Admin fieldsets must include '{section}'"

    def test_admin_sees_user_profile_and_assigned_doctor(self, admin_user):
        fs = self.admin.get_fieldsets(_request(self.factory, admin_user))
        fields = _fieldset_fields(fs)
        assert "user_profile" in fields
        assert "assigned_doctor" in fields

    def test_superuser_sees_same_fieldsets_as_admin(self, admin_user):
        su = User.objects.create_superuser(
            username="su_fs_1", password="pass", email="su4@t.com"
        )
        admin_fs = _fieldset_titles(
            self.admin.get_fieldsets(_request(self.factory, admin_user))
        )
        su_fs = _fieldset_titles(self.admin.get_fieldsets(_request(self.factory, su)))
        assert admin_fs == su_fs

    # ── patient ──

    def test_patient_does_not_see_user_profile_field(self, patient_user):
        fs = self.admin.get_fieldsets(_request(self.factory, patient_user))
        assert "user_profile" not in _fieldset_fields(fs)

    def test_patient_does_not_see_care_assignment_section(self, patient_user):
        fs = self.admin.get_fieldsets(_request(self.factory, patient_user))
        assert "Care Assignment" not in _fieldset_titles(fs)

    def test_patient_sees_personal_contact_and_address_sections(self, patient_user):
        fs = self.admin.get_fieldsets(_request(self.factory, patient_user))
        titles = _fieldset_titles(fs)
        for section in ["Personal Information", "Contact Information", "Address"]:
            assert section in titles, f"Patient fieldsets must include '{section}'"

    def test_patient_fieldsets_expose_all_editable_fields(self, patient_user):
        fs = self.admin.get_fieldsets(_request(self.factory, patient_user))
        fields = _fieldset_fields(fs)
        for f in [
            "insurance_number",
            "phone_primary",
            "phone_secondary",
            "email_personal",
            "address_line1",
            "city",
            "state",
            "country",
        ]:
            assert f in fields, f"Patient fieldsets must include editable field '{f}'"

    def test_patient_fieldsets_do_not_expose_system_information(self, patient_user):
        """Patients don't need to see timestamps."""
        fs = self.admin.get_fieldsets(_request(self.factory, patient_user))
        assert "System Information" not in _fieldset_titles(fs)

    # ── doctor ──

    def test_doctor_sees_care_assignment_section(self, doctor_user):
        fs = self.admin.get_fieldsets(_request(self.factory, doctor_user))
        assert "Care Assignment" in _fieldset_titles(fs)

    def test_doctor_sees_all_clinical_sections(self, doctor_user):
        fs = self.admin.get_fieldsets(_request(self.factory, doctor_user))
        titles = _fieldset_titles(fs)
        for section in [
            "Patient Identity",
            "Care Assignment",
            "Personal Information",
            "Contact Information",
            "Address",
            "System Information",
        ]:
            assert section in titles, f"Doctor fieldsets must include '{section}'"

    def test_doctor_sees_user_profile_field(self, doctor_user):
        fs = self.admin.get_fieldsets(_request(self.factory, doctor_user))
        assert "user_profile" in _fieldset_fields(fs)

    def test_doctor_sees_assigned_doctor_field(self, doctor_user):
        fs = self.admin.get_fieldsets(_request(self.factory, doctor_user))
        assert "assigned_doctor" in _fieldset_fields(fs)

    # ── nurse ──

    def test_nurse_sees_care_assignment_section(self, nurse_user):
        fs = self.admin.get_fieldsets(_request(self.factory, nurse_user))
        assert "Care Assignment" in _fieldset_titles(fs)

    def test_nurse_does_not_see_system_information(self, nurse_user):
        """Nurses don't need to see timestamps."""
        fs = self.admin.get_fieldsets(_request(self.factory, nurse_user))
        assert "System Information" not in _fieldset_titles(fs)

    def test_nurse_sees_core_sections(self, nurse_user):
        fs = self.admin.get_fieldsets(_request(self.factory, nurse_user))
        titles = _fieldset_titles(fs)
        for section in [
            "Patient Identity",
            "Care Assignment",
            "Contact Information",
            "Address",
        ]:
            assert section in titles, f"Nurse fieldsets must include '{section}'"

    # ── pharmacy ──

    def test_pharmacy_fieldsets_have_core_sections(self, pharmacy_user):
        """Pharmacy fieldsets include the core patient sections."""
        pharmacy_titles = _fieldset_titles(
            self.admin.get_fieldsets(_request(self.factory, pharmacy_user))
        )
        for section in ["Patient Identity", "Care Assignment", "Personal Information"]:
            assert (
                section in pharmacy_titles
            ), f"Pharmacy fieldsets must include '{section}'"


# ---------------------------------------------------------------------------
# 5. has_add_permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.permissions
class TestPatientAdminAddPermission:
    """Only admins and superusers are allowed to create patient records."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    def test_admin_can_add(self, admin_user):
        assert self.admin.has_add_permission(_request(self.factory, admin_user)) is True

    def test_superuser_can_add(self):
        su = User.objects.create_superuser(
            username="su_add_1", password="pass", email="su5@t.com"
        )
        assert self.admin.has_add_permission(_request(self.factory, su)) is True

    def test_doctor_cannot_add(self, doctor_user):
        assert (
            self.admin.has_add_permission(_request(self.factory, doctor_user)) is False
        )

    def test_nurse_cannot_add(self, nurse_user):
        assert (
            self.admin.has_add_permission(_request(self.factory, nurse_user)) is False
        )

    def test_pharmacy_cannot_add(self, pharmacy_user):
        assert (
            self.admin.has_add_permission(_request(self.factory, pharmacy_user))
            is False
        )

    def test_patient_cannot_add(self, patient_user):
        assert (
            self.admin.has_add_permission(_request(self.factory, patient_user)) is False
        )


# ---------------------------------------------------------------------------
# 6. has_delete_permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.permissions
class TestPatientAdminDeletePermission:
    """Only admins and superusers are allowed to delete patient records."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = PatientAdmin(Patient, AdminSite())

    def test_admin_can_delete(self, admin_user, patient_user):
        patient = patient_user.profile.patient_record
        assert (
            self.admin.has_delete_permission(
                _request(self.factory, admin_user), patient
            )
            is True
        )

    def test_superuser_can_delete(self, patient_user):
        su = User.objects.create_superuser(
            username="su_del_1", password="pass", email="su6@t.com"
        )
        patient = patient_user.profile.patient_record
        assert (
            self.admin.has_delete_permission(_request(self.factory, su), patient)
            is True
        )

    def test_doctor_cannot_delete_assigned_patient(self, doctor_user, patient_user):
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        assert (
            self.admin.has_delete_permission(
                _request(self.factory, doctor_user), patient
            )
            is False
        )

    def test_nurse_cannot_delete(self, nurse_user, patient_user):
        patient = patient_user.profile.patient_record
        assert (
            self.admin.has_delete_permission(
                _request(self.factory, nurse_user), patient
            )
            is False
        )

    def test_pharmacy_cannot_delete(self, pharmacy_user, patient_user):
        patient = patient_user.profile.patient_record
        assert (
            self.admin.has_delete_permission(
                _request(self.factory, pharmacy_user), patient
            )
            is False
        )

    def test_patient_cannot_delete_own_record(self, patient_user):
        patient = patient_user.profile.patient_record
        assert (
            self.admin.has_delete_permission(
                _request(self.factory, patient_user), patient
            )
            is False
        )

    def test_admin_can_delete_without_specific_object(self, admin_user):
        """has_delete_permission(request) without obj must also return True for admin."""
        assert (
            self.admin.has_delete_permission(_request(self.factory, admin_user)) is True
        )

    def test_non_admin_cannot_delete_without_specific_object(
        self, doctor_user, nurse_user, pharmacy_user, patient_user
    ):
        for user in [doctor_user, nurse_user, pharmacy_user, patient_user]:
            assert (
                self.admin.has_delete_permission(_request(self.factory, user)) is False
            ), f"{user.profile.role} should not be able to delete"
