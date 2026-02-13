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
