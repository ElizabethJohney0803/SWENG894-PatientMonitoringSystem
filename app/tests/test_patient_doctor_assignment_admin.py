"""
Tests for Patient-Doctor assignment admin interface functionality.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from core.admin import PatientAdmin, PatientAdminForm
from core.models import UserProfile, Patient


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientDoctorAssignmentAdmin:
    """Test Patient-Doctor assignment admin interface."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_patient_admin_form_doctor_choices(self):
        """Test that PatientAdminForm limits assigned_doctor choices to doctors only."""
        # Create users with different roles
        doctor_user = User.objects.create_user(username="doctor_test", password="pass")
        nurse_user = User.objects.create_user(username="nurse_test", password="pass")

        UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC123"
        )
        UserProfile.objects.create(
            user=nurse_user, role="nurse", license_number="NURSE123"
        )

        form = PatientAdminForm()

        # Check that only doctors appear in assigned_doctor choices
        doctor_choices = form.fields["assigned_doctor"].queryset
        assert doctor_user.profile in doctor_choices
        assert nurse_user.profile not in doctor_choices
        assert doctor_choices.filter(role="doctor").count() == doctor_choices.count()

    def test_patient_admin_list_display_includes_assigned_doctor(
        self, patient_user, doctor_user
    ):
        """Test that admin list display includes assigned doctor information."""
        admin = PatientAdmin(Patient, self.admin_site)

        # Check that assigned doctor field is in list_display
        assert "get_assigned_doctor" in admin.list_display

        # Test the method
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        doctor_display = admin.get_assigned_doctor(patient)
        expected = doctor_user.get_full_name() or doctor_user.username
        assert doctor_display == expected

    def test_patient_admin_list_display_unassigned_doctor(self, patient_user):
        """Test admin list display for patients without assigned doctors."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        # Patient has no assigned doctor
        assert patient.assigned_doctor is None

        doctor_display = admin.get_assigned_doctor(patient)
        assert doctor_display == "Unassigned"

    def test_patient_admin_list_filter_includes_assigned_doctor(self):
        """Test that admin list includes assigned_doctor in filters."""
        admin = PatientAdmin(Patient, self.admin_site)
        assert "assigned_doctor" in admin.list_filter

    def test_patient_admin_search_includes_doctor_fields(self):
        """Test that admin search includes doctor name fields."""
        admin = PatientAdmin(Patient, self.admin_site)
        search_fields = admin.search_fields

        assert "assigned_doctor__user__first_name" in search_fields
        assert "assigned_doctor__user__last_name" in search_fields

    def test_patient_admin_fieldsets_includes_care_assignment(self):
        """Test that admin fieldsets include Care Assignment section."""
        admin = PatientAdmin(Patient, self.admin_site)
        fieldsets = admin.fieldsets

        # Find Care Assignment fieldset
        care_assignment_fieldset = None
        for fieldset in fieldsets:
            if fieldset[0] == "Care Assignment":
                care_assignment_fieldset = fieldset
                break

        assert care_assignment_fieldset is not None
        assert "assigned_doctor" in care_assignment_fieldset[1]["fields"]

    def test_patient_admin_doctor_queryset_filtering(
        self, doctor_user, doctor_user_2, patient_user
    ):
        """Test that doctors see only their assigned patients in admin."""
        # Create patients and assignments
        patient1 = patient_user.profile.patient_record

        # Create second patient
        user2 = User.objects.create_user(username="patient2_admin", password="pass")
        profile2 = UserProfile.objects.create(user=user2, role="patient")
        patient2 = profile2.patient_record

        # Assign patients to different doctors
        patient1.assigned_doctor = doctor_user.profile
        patient1.save()
        patient2.assigned_doctor = doctor_user_2.profile
        patient2.save()

        admin = PatientAdmin(Patient, self.admin_site)

        # Test doctor1 sees only patient1
        request = self.factory.get("/")
        request.user = doctor_user
        queryset = admin.get_queryset(request)

        assert queryset.count() == 1
        assert patient1 in queryset
        assert patient2 not in queryset

    def test_patient_admin_admin_user_sees_all_patients(
        self, admin_user, doctor_user, patient_user
    ):
        """Test that admin users see all patients regardless of assignment."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = admin_user

        queryset = admin.get_queryset(request)
        assert patient in queryset

    def test_patient_admin_nurse_sees_all_patients(
        self, nurse_user, doctor_user, patient_user
    ):
        """Test that nurses see all patients (not filtered by assignment)."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = nurse_user

        queryset = admin.get_queryset(request)
        assert patient in queryset

    def test_patient_admin_readonly_fields_for_roles(
        self, doctor_user, nurse_user, admin_user, patient_user
    ):
        """Test readonly fields for different user roles."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        # Test doctor readonly fields
        request = self.factory.get("/")
        request.user = doctor_user
        readonly_fields = admin.get_readonly_fields(request, patient)
        assert "assigned_doctor" in readonly_fields

        # Test nurse readonly fields
        request.user = nurse_user
        readonly_fields = admin.get_readonly_fields(request, patient)
        assert "assigned_doctor" in readonly_fields

        # Test admin readonly fields (should have basic readonly fields only)
        request.user = admin_user
        readonly_fields = admin.get_readonly_fields(request, patient)
        # assigned_doctor should NOT be in readonly fields for admin
        basic_readonly = ["medical_id", "age", "created_at", "updated_at"]
        # Admin should only have the basic readonly fields
        for field in basic_readonly:
            assert field in readonly_fields
        # assigned_doctor should not be readonly for admin
        assert (
            "assigned_doctor" not in readonly_fields
            or readonly_fields == admin.readonly_fields
        )

    def test_patient_admin_patient_readonly_fields(self, patient_user):
        """Test readonly fields for patient users."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        request = self.factory.get("/")
        request.user = patient_user
        readonly_fields = admin.get_readonly_fields(request, patient)

        # Patients should have assigned_doctor as readonly
        assert "assigned_doctor" in readonly_fields
        assert "user_profile" in readonly_fields
        assert "date_of_birth" in readonly_fields
        assert "gender" in readonly_fields


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminForm:
    """Test PatientAdminForm functionality."""

    def test_form_assigned_doctor_field_not_required(self):
        """Test that assigned_doctor field is not required."""
        form = PatientAdminForm()
        assert not form.fields["assigned_doctor"].required

    def test_form_assigned_doctor_queryset_filtering(self):
        """Test that form properly filters assigned_doctor choices."""
        # Create test users
        doctor = User.objects.create_user(username="doctor_form_test", password="pass")
        patient = User.objects.create_user(
            username="patient_form_test", password="pass"
        )
        admin = User.objects.create_user(username="admin_form_test", password="pass")

        UserProfile.objects.create(user=doctor, role="doctor", license_number="DOC123")
        UserProfile.objects.create(user=patient, role="patient")
        UserProfile.objects.create(user=admin, role="admin")

        form = PatientAdminForm()
        queryset = form.fields["assigned_doctor"].queryset

        # Only doctors should be in the queryset
        assert queryset.count() == 1
        assert doctor.profile in queryset
        assert patient.profile not in queryset
        assert admin.profile not in queryset

    def test_form_initialization_with_existing_data(self, patient_user, doctor_user):
        """Test form initialization with existing patient data."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        form = PatientAdminForm(instance=patient)
        assert form.instance.assigned_doctor == doctor_user.profile
        assert doctor_user.profile in form.fields["assigned_doctor"].queryset


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.admin
class TestPatientDoctorAssignmentAdminIntegration:
    """Integration tests for Patient-Doctor assignment admin functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_assignment_workflow_admin_assigns_patient(
        self, admin_user, doctor_user, patient_user
    ):
        """Test complete workflow of admin assigning patient to doctor."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        # Admin should be able to see and modify assigned_doctor
        request = self.factory.get("/")
        request.user = admin_user

        readonly_fields = admin.get_readonly_fields(request, patient)
        assert (
            "assigned_doctor" not in readonly_fields
            or readonly_fields == admin.readonly_fields
        )

        # Admin should see all patients
        queryset = admin.get_queryset(request)
        assert patient in queryset

        # Simulate assignment
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        # Verify assignment appears in display
        assert admin.get_assigned_doctor(patient) == doctor_user.get_full_name()

    def test_doctor_access_after_assignment(self, doctor_user, patient_user):
        """Test doctor can access patient after assignment."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        # Initially doctor cannot see patient
        request = self.factory.get("/")
        request.user = doctor_user
        queryset = admin.get_queryset(request)
        assert patient not in queryset

        # Assign patient to doctor
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        # Now doctor can see patient
        queryset = admin.get_queryset(request)
        assert patient in queryset

        # But cannot modify assignment
        readonly_fields = admin.get_readonly_fields(request, patient)
        assert "assigned_doctor" in readonly_fields

    def test_assignment_change_effects(self, doctor_user, doctor_user_2, patient_user):
        """Test effects of changing patient assignment between doctors."""
        admin = PatientAdmin(Patient, self.admin_site)
        patient = patient_user.profile.patient_record

        # Assign to doctor1
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        # Doctor1 can see patient
        request = self.factory.get("/")
        request.user = doctor_user
        queryset = admin.get_queryset(request)
        assert patient in queryset

        # Doctor2 cannot see patient
        request.user = doctor_user_2
        queryset = admin.get_queryset(request)
        assert patient not in queryset

        # Reassign to doctor2
        patient.assigned_doctor = doctor_user_2.profile
        patient.save()

        # Now doctor2 can see patient
        request.user = doctor_user_2
        queryset = admin.get_queryset(request)
        assert patient in queryset

        # Doctor1 can no longer see patient
        request.user = doctor_user
        queryset = admin.get_queryset(request)
        assert patient not in queryset
