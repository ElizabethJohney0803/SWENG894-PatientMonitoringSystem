"""
Tests for patient admin access and permissions.
Covers the acceptance criteria for patient users accessing their data through Django admin.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase, RequestFactory
from django.test.client import Client
from unittest.mock import Mock, patch

from core.admin import PatientAdmin, UserProfileAdmin, EmergencyContactAdmin
from core.models import UserProfile, Patient, EmergencyContact
from core.mixins import PatientAccessMixin


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.patient_access
class TestPatientAdminAccess:
    """Test patient users' access to Django admin interface."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    @pytest.fixture
    def patient_user_with_record(self, patient_user):
        """Create a patient user with associated Patient record."""
        # Ensure Patient record exists
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        # Add some test data
        patient_record.date_of_birth = "1990-01-01"
        patient_record.gender = "M"
        patient_record.blood_type = "A+"
        patient_record.phone_primary = "555-0123"
        patient_record.address_line1 = "123 Test St"
        patient_record.city = "Test City"
        patient_record.state = "TS"
        patient_record.save()

        return patient_user, patient_record

    def test_patient_has_module_permission(self, patient_user):
        """Test that patients can access the Patient admin module."""
        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # Patients should have module permission for Patient admin
        assert patient_admin.has_module_permission(request) is True

    def test_patient_denied_userprofile_module_permission(self, patient_user):
        """Test that patients cannot access UserProfile admin module."""
        request = self.factory.get("/admin/core/userprofile/")
        request.user = patient_user

        userprofile_admin = UserProfileAdmin(UserProfile, self.admin_site)

        # Patients should NOT have module permission for UserProfile admin
        assert userprofile_admin.has_module_permission(request) is False

    def test_patient_can_view_own_patient_record(self, patient_user_with_record):
        """Test that patients can view their own Patient record."""
        patient_user, patient_record = patient_user_with_record

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # Patient should have view permission for their own record
        assert patient_admin.has_view_permission(request) is True
        assert patient_admin.has_view_permission(request, patient_record) is True

    def test_patient_can_change_own_patient_record(self, patient_user_with_record):
        """Test that patients can change their own Patient record."""
        patient_user, patient_record = patient_user_with_record

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # Patient should have change permission for their own record
        assert patient_admin.has_change_permission(request) is True
        assert patient_admin.has_change_permission(request, patient_record) is True

    def test_patient_cannot_delete_own_patient_record(self, patient_user_with_record):
        """Test that patients cannot delete their own Patient record."""
        patient_user, patient_record = patient_user_with_record

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # Patient should NOT have delete permission for their own record
        assert patient_admin.has_delete_permission(request, patient_record) is False

    def test_patient_cannot_access_other_patient_records(
        self, patient_user, doctor_user
    ):
        """Test that patients cannot access other patients' records."""
        # Create another patient
        other_patient_user = User.objects.create_user(
            username="other_patient", password="testpass123"
        )
        other_patient_profile = UserProfile.objects.create(
            user=other_patient_user, role="patient"
        )
        other_patient_profile.ensure_patient_record()
        other_patient_record = Patient.objects.get(user_profile=other_patient_profile)

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # Patient should not have access to other patient's record
        assert patient_admin.has_view_permission(request, other_patient_record) is False
        assert (
            patient_admin.has_change_permission(request, other_patient_record) is False
        )
        assert (
            patient_admin.has_delete_permission(request, other_patient_record) is False
        )

    def test_patient_queryset_filtered_to_own_records(self, patient_user_with_record):
        """Test that patient queryset is filtered to show only their own records."""
        patient_user, patient_record = patient_user_with_record

        # Create another patient record
        other_user = User.objects.create_user(username="other", password="pass")
        other_profile = UserProfile.objects.create(user=other_user, role="patient")
        other_profile.ensure_patient_record()

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)
        queryset = patient_admin.get_queryset(request)

        # Should only contain patient's own record
        assert queryset.count() == 1
        assert queryset.first() == patient_record

    def test_patient_auto_record_creation_on_changelist(self, patient_user):
        """Test that Patient record is auto-created when patient visits changelist."""
        # Ensure no Patient record exists initially
        assert not hasattr(patient_user.profile, "patient")

        request = self.factory.get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, self.admin_site)

        # This should trigger auto-creation
        patient_admin.changelist_view(request)

        # Patient record should now exist
        patient_user.profile.refresh_from_db()
        assert Patient.objects.filter(user_profile=patient_user.profile).exists()

    def test_patient_staff_status_granted(self):
        """Test that patient users automatically get staff status for admin access."""
        user = User.objects.create_user(
            username="new_patient",
            password="testpass123",
            is_staff=False,  # Initially not staff
        )

        # Creating profile should grant staff status
        profile = UserProfile.objects.create(user=user, role="patient")

        user.refresh_from_db()
        assert user.is_staff is True


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.emergency_contacts
class TestPatientEmergencyContactAccess:
    """Test patient users' access to emergency contacts."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    @pytest.fixture
    def patient_with_emergency_contact(self, patient_user):
        """Create patient with emergency contact."""
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        emergency_contact = EmergencyContact.objects.create(
            patient=patient_record,
            name="John Doe",
            relationship="Spouse",
            phone_primary="555-0199",
            email="john@example.com",
            is_primary_contact=True,
        )

        return patient_user, patient_record, emergency_contact

    def test_patient_can_manage_own_emergency_contacts(
        self, patient_with_emergency_contact
    ):
        """Test that patients can manage their own emergency contacts."""
        patient_user, patient_record, emergency_contact = patient_with_emergency_contact

        request = self.factory.get("/admin/core/emergencycontact/")
        request.user = patient_user

        emergency_admin = EmergencyContactAdmin(EmergencyContact, self.admin_site)

        # Patient should have permissions for their own emergency contacts
        assert emergency_admin.has_view_permission(request, emergency_contact) is True
        assert emergency_admin.has_change_permission(request, emergency_contact) is True
        assert emergency_admin.has_add_permission(request) is True
        assert emergency_admin.has_delete_permission(request, emergency_contact) is True

    def test_patient_emergency_contact_queryset_filtered(
        self, patient_with_emergency_contact
    ):
        """Test that emergency contact queryset is filtered to patient's contacts only."""
        patient_user, patient_record, emergency_contact = patient_with_emergency_contact

        # Create emergency contact for another patient
        other_user = User.objects.create_user(username="other", password="pass")
        other_profile = UserProfile.objects.create(user=other_user, role="patient")
        other_profile.ensure_patient_record()
        other_patient = Patient.objects.get(user_profile=other_profile)

        other_emergency_contact = EmergencyContact.objects.create(
            patient=other_patient,
            name="Jane Smith",
            relationship="Mother",
            phone_primary="555-0188",
        )

        request = self.factory.get("/admin/core/emergencycontact/")
        request.user = patient_user

        emergency_admin = EmergencyContactAdmin(EmergencyContact, self.admin_site)
        queryset = emergency_admin.get_queryset(request)

        # Should only contain patient's own emergency contacts
        assert queryset.count() == 1
        assert queryset.first() == emergency_contact


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.admin_templates
class TestPatientAdminTemplates:
    """Test custom admin templates for patient experience."""

    def test_patient_admin_index_template_context(self, patient_user):
        """Test that patient admin index provides correct context."""
        client = Client()

        # Login as patient
        client.force_login(patient_user)

        # Test admin index
        response = client.get("/admin/")

        # Should render without error and contain patient-specific content
        assert response.status_code == 200
        # Template should handle patient role
        assert "admin/index.html" in [t.name for t in response.templates]

    def test_patient_changelist_view_context(self, patient_user):
        """Test that patient changelist view provides helpful context."""
        patient_user.profile.ensure_patient_record()

        client = Client()
        client.force_login(patient_user)

        response = client.get("/admin/core/patient/")

        # Should render successfully
        assert response.status_code == 200
        # Should contain patient help message in context
        assert "patient_help_message" in response.context


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.role_permissions
class TestRoleBasedPermissionBypass:
    """Test that role-based users bypass Django's default permission system."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()

    def test_role_based_mixin_bypasses_django_permissions(self, patient_user):
        """Test that RoleBasedAdminMixin bypasses Django permissions for role users."""

        class TestPatientAdmin(PatientAccessMixin):
            model = Patient

        admin_instance = TestPatientAdmin()
        request = self.factory.get("/")
        request.user = patient_user

        # Even without explicit Django permissions, role-based users should have access
        assert admin_instance.has_view_permission(request) is True
        assert admin_instance.has_change_permission(request) is True
        assert admin_instance.has_add_permission(request) is True

    def test_users_without_roles_fall_back_to_django_permissions(self):
        """Test that users without roles fall back to Django's permission system."""
        user_without_profile = User.objects.create_user(
            username="no_profile", password="testpass123"
        )

        class TestPatientAdmin(PatientAccessMixin):
            model = Patient

        admin_instance = TestPatientAdmin()
        request = self.factory.get("/")
        request.user = user_without_profile

        # Users without profiles should fall back to Django permissions (False)
        assert admin_instance.has_view_permission(request) is False
        assert admin_instance.has_change_permission(request) is False
        assert admin_instance.has_add_permission(request) is False


@pytest.mark.django_db
@pytest.mark.acceptance
class TestPatientAdminAcceptanceCriteria:
    """Test acceptance criteria for patient admin access."""

    def test_ac001_patient_sees_patient_admin_not_userprofile(self, patient_user):
        """AC-001: Patient users see Patient admin, not UserProfile admin."""
        request = RequestFactory().get("/admin/")
        request.user = patient_user

        # Patient admin should be accessible
        patient_admin = PatientAdmin(Patient, AdminSite())
        assert patient_admin.has_module_permission(request) is True

        # UserProfile admin should be hidden
        userprofile_admin = UserProfileAdmin(UserProfile, AdminSite())
        assert userprofile_admin.has_module_permission(request) is False

    def test_ac002_patient_can_edit_personal_info_and_emergency_contacts(
        self, patient_user
    ):
        """AC-002: Patient can edit personal information and emergency contacts."""
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        request = RequestFactory().get("/admin/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, AdminSite())

        # Should be able to view and change their own record
        assert patient_admin.has_view_permission(request, patient_record) is True
        assert patient_admin.has_change_permission(request, patient_record) is True

        # Should be able to manage emergency contacts
        emergency_admin = EmergencyContactAdmin(EmergencyContact, AdminSite())
        assert emergency_admin.has_add_permission(request) is True

    def test_ac003_patient_cannot_delete_own_record(self, patient_user):
        """AC-003: Patient cannot delete their own Patient record."""
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        request = RequestFactory().get("/admin/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, AdminSite())

        # Should NOT be able to delete their own record
        assert patient_admin.has_delete_permission(request, patient_record) is False

    def test_ac004_patient_only_sees_own_data(self, patient_user):
        """AC-004: Patient only sees their own data, not other patients'."""
        # Create patient record
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        # Create another patient
        other_user = User.objects.create_user(username="other", password="pass")
        other_profile = UserProfile.objects.create(user=other_user, role="patient")
        other_profile.ensure_patient_record()

        request = RequestFactory().get("/admin/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, AdminSite())
        queryset = patient_admin.get_queryset(request)

        # Should only see their own record
        assert queryset.count() == 1
        assert queryset.first() == patient_record

    def test_ac005_patient_auto_record_creation(self, patient_user):
        """AC-005: Patient record is automatically created for patient users."""
        # Initially no Patient record
        assert not Patient.objects.filter(user_profile=patient_user.profile).exists()

        # Accessing admin should trigger auto-creation
        request = RequestFactory().get("/admin/core/patient/")
        request.user = patient_user

        patient_admin = PatientAdmin(Patient, AdminSite())
        patient_admin.changelist_view(request)

        # Patient record should now exist
        assert Patient.objects.filter(user_profile=patient_user.profile).exists()

    def test_ac006_patient_gets_staff_status_for_admin_access(self):
        """AC-006: Patient users get staff status to access admin interface."""
        user = User.objects.create_user(
            username="test_patient", password="pass", is_staff=False
        )

        # Creating patient profile should grant staff status
        profile = UserProfile.objects.create(user=user, role="patient")

        user.refresh_from_db()
        assert user.is_staff is True
