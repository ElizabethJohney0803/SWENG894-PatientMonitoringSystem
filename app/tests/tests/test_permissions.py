"""
Tests for permission mixins and role-based access control.
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
from core.admin import UserAdmin, UserProfileAdmin
from core.mixins import (
    AdminOnlyMixin,
    PatientAccessMixin,
    MedicalStaffMixin,
    DoctorOnlyMixin,
)
from core.models import UserProfile


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.permissions
class TestPatientDoctorAssignmentPermissions:
    """Test Patient-Doctor assignment permission functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_doctor_queryset_filtering(self, doctor_user, patient_user, doctor_user_2):
        """Test that doctors only see their assigned patients."""
        from core.admin import PatientAdmin
        from core.models import Patient

        # Create patients
        patient1 = patient_user.profile.patient_record

        # Create second patient
        user2 = User.objects.create_user(username="patient2", password="pass")
        profile2 = UserProfile.objects.create(user=user2, role="patient")
        patient2 = profile2.patient_record

        # Assign patient1 to doctor1, patient2 to doctor2
        patient1.assigned_doctor = doctor_user.profile
        patient1.save()
        patient2.assigned_doctor = doctor_user_2.profile
        patient2.save()

        # Test doctor1 can only see patient1
        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = doctor_user

        queryset = admin.get_queryset(request)
        assert queryset.count() == 1
        assert patient1 in queryset
        assert patient2 not in queryset

        # Test doctor2 can only see patient2
        request.user = doctor_user_2
        queryset = admin.get_queryset(request)
        assert queryset.count() == 1
        assert patient2 in queryset
        assert patient1 not in queryset

    def test_admin_can_see_all_patients(self, admin_user, doctor_user, patient_user):
        """Test that admin can see all patients regardless of assignment."""
        from core.admin import PatientAdmin
        from core.models import Patient

        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = admin_user

        queryset = admin.get_queryset(request)
        assert patient in queryset

    def test_doctor_readonly_assigned_doctor_field(self, doctor_user, patient_user):
        """Test that doctors cannot modify assigned_doctor field."""
        from core.admin import PatientAdmin
        from core.models import Patient

        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = doctor_user

        readonly_fields = admin.get_readonly_fields(request, patient)
        assert "assigned_doctor" in readonly_fields

    def test_admin_can_modify_assigned_doctor_field(self, admin_user, patient_user):
        """Test that admin can modify assigned_doctor field."""
        from core.admin import PatientAdmin
        from core.models import Patient

        patient = patient_user.profile.patient_record

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = admin_user

        readonly_fields = admin.get_readonly_fields(request, patient)
        assert (
            "assigned_doctor" not in readonly_fields
            or readonly_fields == admin.readonly_fields
        )

    def test_patient_cannot_modify_assigned_doctor_field(self, patient_user):
        """Test that patients cannot modify assigned_doctor field."""
        from core.admin import PatientAdmin
        from core.models import Patient

        patient = patient_user.profile.patient_record

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = patient_user

        readonly_fields = admin.get_readonly_fields(request, patient)
        assert "assigned_doctor" in readonly_fields

    def test_doctor_only_mixin_filtering(self, doctor_user, patient_user):
        """Test DoctorOnlyMixin filtering for assigned patients."""
        from core.mixins import DoctorOnlyMixin
        from core.models import Patient

        # Create test admin class with mixin
        class TestDoctorAdmin(DoctorOnlyMixin):
            def get_queryset(self, request):
                from django.contrib.admin import ModelAdmin

                qs = Patient.objects.all()
                return (
                    super().get_queryset(request)
                    if hasattr(super(), "get_queryset")
                    else qs
                )

        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        admin = TestDoctorAdmin()
        request = self.factory.get("/")
        request.user = doctor_user

        # Test filtering method directly
        queryset = Patient.objects.all()
        filtered_qs = admin.filter_queryset_by_role(request, queryset, "doctor")

        assert patient in filtered_qs
        assert filtered_qs.count() == 1

    def test_unassigned_patients_invisible_to_doctors(self, doctor_user, patient_user):
        """Test that doctors cannot see unassigned patients."""
        from core.admin import PatientAdmin
        from core.models import Patient

        # Patient has no assigned doctor
        patient = patient_user.profile.patient_record
        assert patient.assigned_doctor is None

        admin = PatientAdmin(Patient, self.admin_site)
        request = self.factory.get("/")
        request.user = doctor_user

        queryset = admin.get_queryset(request)
        assert patient not in queryset
        assert queryset.count() == 0


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.permissions
class TestPermissionMixins:
    """Test role-based permission mixins."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_admin_only_mixin_superuser_access(self, admin_user):
        """Test AdminOnlyMixin allows superuser access."""
        # Make user a superuser
        admin_user.is_superuser = True
        admin_user.save()

        class TestAdminOnlyAdmin(AdminOnlyMixin):
            pass

        admin_instance = TestAdminOnlyAdmin()
        request = self.factory.get("/")
        request.user = admin_user

        assert admin_instance.check_role_permission(request, None, "add") is True
        assert admin_instance.check_role_permission(request, None, "view") is True
        assert admin_instance.check_role_permission(request, None, "change") is True
        assert admin_instance.check_role_permission(request, None, "delete") is True

    def test_admin_only_mixin_admin_role_access(self, admin_user):
        """Test AdminOnlyMixin allows admin role access."""

        class TestAdminOnlyAdmin(AdminOnlyMixin):
            pass

        admin_instance = TestAdminOnlyAdmin()
        request = self.factory.get("/")
        request.user = admin_user

        assert admin_instance.check_role_permission(request, None, "add") is True
        assert admin_instance.check_role_permission(request, None, "view") is True
        assert admin_instance.check_role_permission(request, None, "change") is True
        assert admin_instance.check_role_permission(request, None, "delete") is True

    def test_admin_only_mixin_denies_other_roles(
        self, doctor_user, nurse_user, patient_user
    ):
        """Test AdminOnlyMixin denies access to non-admin roles."""

        class TestAdminOnlyAdmin(AdminOnlyMixin):
            pass

        admin_instance = TestAdminOnlyAdmin()

        for user in [doctor_user, nurse_user, patient_user]:
            request = self.factory.get("/")
            request.user = user

            assert admin_instance.check_role_permission(request, None, "add") is False
            assert admin_instance.check_role_permission(request, None, "view") is False
            assert (
                admin_instance.check_role_permission(request, None, "change") is False
            )
            assert (
                admin_instance.check_role_permission(request, None, "delete") is False
            )

    def test_patient_access_mixin_own_data_only(self, patient_user, doctor_user):
        """Test PatientAccessMixin allows patients to access only their own data."""

        class TestPatientAccessAdmin(PatientAccessMixin):
            pass

        admin_instance = TestPatientAccessAdmin()
        request = self.factory.get("/")
        request.user = patient_user

        # Mock objects with user attribute
        own_obj = type("MockObj", (), {"user": patient_user})()
        other_obj = type("MockObj", (), {"user": doctor_user})()

        # Patient can access their own data
        assert admin_instance.check_role_permission(request, own_obj, "view") is True
        assert admin_instance.check_role_permission(request, own_obj, "change") is True

        # Patient cannot access other user's data
        assert admin_instance.check_role_permission(request, other_obj, "view") is False
        assert (
            admin_instance.check_role_permission(request, other_obj, "change") is False
        )

    def test_medical_staff_mixin_allows_medical_roles(
        self, doctor_user, nurse_user, pharmacy_user
    ):
        """Test MedicalStaffMixin allows access to medical staff roles."""

        class TestMedicalStaffAdmin(MedicalStaffMixin):
            pass

        admin_instance = TestMedicalStaffAdmin()

        for user in [doctor_user, nurse_user, pharmacy_user]:
            request = self.factory.get("/")
            request.user = user

            assert admin_instance.check_role_permission(request, None, "view") is True
            assert admin_instance.check_role_permission(request, None, "change") is True

    def test_medical_staff_mixin_denies_patient(self, patient_user):
        """Test MedicalStaffMixin denies access to patients."""

        class TestMedicalStaffAdmin(MedicalStaffMixin):
            pass

        admin_instance = TestMedicalStaffAdmin()
        request = self.factory.get("/")
        request.user = patient_user

        assert admin_instance.check_role_permission(request, None, "view") is False
        assert admin_instance.check_role_permission(request, None, "change") is False

    def test_doctor_only_mixin(self, doctor_user, admin_user, nurse_user, patient_user):
        """Test DoctorOnlyMixin allows only doctors and admins."""

        class TestDoctorOnlyAdmin(DoctorOnlyMixin):
            pass

        admin_instance = TestDoctorOnlyAdmin()

        # Allowed roles
        for user in [doctor_user, admin_user]:
            request = self.factory.get("/")
            request.user = user
            assert admin_instance.check_role_permission(request, None, "view") is True

        # Denied roles
        for user in [nurse_user, patient_user]:
            request = self.factory.get("/")
            request.user = user
            assert admin_instance.check_role_permission(request, None, "view") is False


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.permissions
class TestAdminPermissions:
    """Test admin interface permissions."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_user_admin_module_permission_for_admin(self, admin_user):
        """Test UserAdmin module permission for admin users."""
        admin_instance = UserAdmin(User, self.admin_site)
        request = self.factory.get("/")
        request.user = admin_user

        assert admin_instance.has_module_permission(request) is True

    def test_user_admin_module_permission_for_superuser(self, admin_user):
        """Test UserAdmin module permission for superusers."""
        admin_user.is_superuser = True
        admin_user.save()

        admin_instance = UserAdmin(User, self.admin_site)
        request = self.factory.get("/")
        request.user = admin_user

        assert admin_instance.has_module_permission(request) is True

    def test_user_admin_module_permission_denied_for_others(
        self, doctor_user, nurse_user, patient_user
    ):
        """Test UserAdmin module permission denied for non-admin users."""
        admin_instance = UserAdmin(User, self.admin_site)

        for user in [doctor_user, nurse_user, patient_user]:
            request = self.factory.get("/")
            request.user = user
            assert admin_instance.has_module_permission(request) is False

    def test_user_admin_queryset_filtering(self, admin_user, doctor_user, sample_users):
        """Test UserAdmin queryset filtering based on user role."""
        admin_instance = UserAdmin(User, self.admin_site)

        # Admin should see all users
        request = self.factory.get("/")
        request.user = admin_user
        queryset = admin_instance.get_queryset(request)
        assert queryset.count() >= 5  # Should see all sample users

        # Non-admin should see no users (empty queryset)
        request.user = doctor_user
        queryset = admin_instance.get_queryset(request)
        assert queryset.count() == 0

    def test_user_profile_admin_queryset_filtering(
        self, admin_user, doctor_user, sample_users
    ):
        """Test UserProfileAdmin queryset filtering."""
        admin_instance = UserProfileAdmin(UserProfile, self.admin_site)

        # Admin should see all profiles
        request = self.factory.get("/")
        request.user = admin_user
        queryset = admin_instance.get_queryset(request)
        assert queryset.count() >= 5  # Should see all sample profiles

        # Doctor should only see own profile
        request.user = doctor_user
        queryset = admin_instance.get_queryset(request)
        assert queryset.count() == 1
        assert queryset.first().user == doctor_user

    def test_user_profile_admin_add_permission(self, admin_user, doctor_user):
        """Test UserProfileAdmin add permission restrictions."""
        admin_instance = UserProfileAdmin(UserProfile, self.admin_site)

        # Admin should have add permission
        request = self.factory.get("/")
        request.user = admin_user
        assert admin_instance.has_add_permission(request) is True

        # Doctor should not have add permission
        request.user = doctor_user
        assert admin_instance.has_add_permission(request) is False

    def test_user_profile_admin_delete_permission(self, admin_user, doctor_user):
        """Test UserProfileAdmin delete permission restrictions."""
        admin_instance = UserProfileAdmin(UserProfile, self.admin_site)

        # Admin should have delete permission
        request = self.factory.get("/")
        request.user = admin_user
        assert admin_instance.has_delete_permission(request) is True

        # Doctor should not have delete permission
        request.user = doctor_user
        assert admin_instance.has_delete_permission(request) is False

    def test_superuser_always_has_permissions(self, doctor_user):
        """Test that superusers always have full permissions regardless of profile role."""
        doctor_user.is_superuser = True
        doctor_user.save()

        # Test UserAdmin
        user_admin = UserAdmin(User, self.admin_site)
        request = self.factory.get("/")
        request.user = doctor_user

        assert user_admin.has_module_permission(request) is True
        assert user_admin.has_add_permission(request) is True
        assert user_admin.has_change_permission(request) is True
        assert user_admin.has_delete_permission(request) is True

        # Test UserProfileAdmin
        profile_admin = UserProfileAdmin(UserProfile, self.admin_site)
        assert profile_admin.has_add_permission(request) is True
        assert profile_admin.has_change_permission(request) is True
        assert profile_admin.has_delete_permission(request) is True

    def test_patient_access_mixin_permission_bypass(self, patient_user):
        """Test that PatientAccessMixin bypasses Django permissions for role-based users."""

        class TestPatientAccessAdmin(PatientAccessMixin):
            pass

        admin_instance = TestPatientAccessAdmin()
        request = self.factory.get("/")
        request.user = patient_user

        # Patient should have view and change permissions without explicit Django perms
        assert admin_instance.has_view_permission(request) is True
        assert admin_instance.has_change_permission(request) is True
        assert admin_instance.has_add_permission(request) is True

    def test_patient_access_mixin_delete_restriction(self, patient_user):
        """Test that patients cannot delete their own records."""
        from core.models import Patient

        # Create patient record
        patient_user.profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        class TestPatientAccessAdmin(PatientAccessMixin):
            pass

        admin_instance = TestPatientAccessAdmin()
        request = self.factory.get("/")
        request.user = patient_user

        # Patient should NOT have delete permission for their own record
        assert admin_instance.has_delete_permission(request, patient_record) is False

    def test_role_based_mixin_fallback_to_django_permissions(self):
        """Test that users without profiles fall back to Django permissions."""
        user_without_profile = User.objects.create_user(
            username="no_profile_user", password="testpass123"
        )

        class TestPatientAccessAdmin(PatientAccessMixin):
            pass

        admin_instance = TestPatientAccessAdmin()
        request = self.factory.get("/")
        request.user = user_without_profile

        # User without profile should fall back to Django permissions (False)
        assert admin_instance.has_view_permission(request) is False
        assert admin_instance.has_change_permission(request) is False
        assert admin_instance.has_add_permission(request) is False
