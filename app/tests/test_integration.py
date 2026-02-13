"""
Integration and system tests for the Patient Monitoring System.
Tests end-to-end workflows and component interactions.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User, Group
from django.test import TestCase, Client
from django.urls import reverse
from core.admin import CustomUserCreationForm, UserAdmin, UserProfileAdmin
from core.models import UserProfile


@pytest.mark.django_db
@pytest.mark.integration
class TestUserCreationWorkflow:
    """Test complete user creation workflow from form to database."""

    def test_complete_doctor_creation_workflow(self, create_groups):
        """Test complete workflow of creating a doctor user."""
        # Step 1: Submit form data
        form_data = {
            "username": "dr_integration",
            "first_name": "Integration",
            "last_name": "Doctor",
            "email": "dr.integration@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "doctor",
            "department": "Neurology",
            "license_number": "MD789012",
            "phone": "555-1111",
        }

        # Step 2: Process form
        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form validation failed: {form.errors}"

        # Step 3: Save user through form
        user = form.save()

        # Step 4: Verify user creation
        assert User.objects.filter(username="dr_integration").exists()
        saved_user = User.objects.get(username="dr_integration")
        assert saved_user.first_name == "Integration"
        assert saved_user.last_name == "Doctor"
        assert saved_user.email == "dr.integration@hospital.com"

        # Step 5: Verify profile creation and data
        assert hasattr(saved_user, "profile")
        profile = saved_user.profile
        assert profile.role == "doctor"
        assert profile.department == "Neurology"
        assert profile.license_number == "MD789012"
        assert profile.phone == "555-1111"

        # Step 6: Verify profile completeness
        assert profile.is_complete is True
        assert profile.is_medical_staff is True
        assert profile.can_access_patient_records is True
        assert profile.can_prescribe_medication is True

        # Step 7: Verify group assignment
        user_groups = list(saved_user.groups.values_list("name", flat=True))
        assert "Doctors" in user_groups
        assert len(user_groups) == 1

        # Step 8: Verify string representation
        expected_str = f"Integration Doctor (Doctor)"
        assert str(profile) == expected_str

    def test_complete_nurse_creation_workflow(self, create_groups):
        """Test complete workflow of creating a nurse user."""
        form_data = {
            "username": "nurse_integration",
            "first_name": "Integration",
            "last_name": "Nurse",
            "email": "nurse.integration@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "nurse",
            "department": "Pediatrics",
            "license_number": "RN789012",
            "phone": "555-2222",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form validation failed: {form.errors}"

        user = form.save()
        profile = user.profile

        # Verify all aspects of nurse creation
        assert profile.role == "nurse"
        assert profile.department == "Pediatrics"
        assert profile.license_number == "RN789012"
        assert profile.is_medical_staff is True
        assert profile.can_access_patient_records is True
        assert profile.can_prescribe_medication is False

        user_groups = list(user.groups.values_list("name", flat=True))
        assert "Nurses" in user_groups

    def test_complete_patient_creation_workflow(self, create_groups):
        """Test complete workflow of creating a patient user."""
        form_data = {
            "username": "patient_integration",
            "first_name": "Integration",
            "last_name": "Patient",
            "email": "patient.integration@email.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "patient",
            "phone": "555-3333",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form validation failed: {form.errors}"

        user = form.save()
        profile = user.profile

        # Verify patient-specific attributes
        assert profile.role == "patient"
        assert profile.department == ""
        assert profile.license_number == ""
        assert profile.is_medical_staff is False
        assert profile.can_access_patient_records is False
        assert profile.can_prescribe_medication is False
        assert profile.can_manage_users is False
        assert profile.is_complete is True  # Patients have no required fields

        user_groups = list(user.groups.values_list("name", flat=True))
        assert "Patients" in user_groups

    def test_role_change_workflow(self, create_groups):
        """Test changing a user's role and verifying all related changes."""
        # Create initial patient
        user = User.objects.create_user(
            username="role_change_test", password="testpass123"
        )
        profile = UserProfile.objects.create(
            user=user, role="patient", phone="555-4444"
        )

        # Verify initial state
        assert "Patients" in user.groups.values_list("name", flat=True)
        assert profile.is_medical_staff is False

        # Change to doctor role
        profile.role = "doctor"
        profile.department = "Oncology"
        profile.license_number = "MD555666"
        profile.save()

        # Refresh from database
        user.refresh_from_db()
        profile.refresh_from_db()

        # Verify role change effects
        assert profile.role == "doctor"
        assert profile.is_medical_staff is True
        assert profile.can_prescribe_medication is True
        assert profile.is_complete is True

        # Verify group reassignment
        user_groups = list(user.groups.values_list("name", flat=True))
        assert "Doctors" in user_groups
        assert "Patients" not in user_groups
        assert len(user_groups) == 1

    def test_bulk_user_creation_and_group_management(self, create_groups):
        """Test creating multiple users and verifying group assignments."""
        users_data = [
            ("bulk_doctor1", "doctor", "Cardiology", "MD001"),
            ("bulk_doctor2", "doctor", "Surgery", "MD002"),
            ("bulk_nurse1", "nurse", "ICU", "RN001"),
            ("bulk_nurse2", "nurse", "Emergency", "RN002"),
            ("bulk_patient1", "patient", None, None),
            ("bulk_patient2", "patient", None, None),
        ]

        created_users = []

        for username, role, department, license_num in users_data:
            user = User.objects.create_user(username=username, password="testpass123")
            profile_data = {"user": user, "role": role}

            if department:
                profile_data["department"] = department
            if license_num:
                profile_data["license_number"] = license_num

            profile = UserProfile.objects.create(**profile_data)
            created_users.append((user, profile))

        # Verify group distributions
        doctors_group = Group.objects.get(name="Doctors")
        nurses_group = Group.objects.get(name="Nurses")
        patients_group = Group.objects.get(name="Patients")

        assert (
            doctors_group.user_set.filter(username__startswith="bulk_doctor").count()
            == 2
        )
        assert (
            nurses_group.user_set.filter(username__startswith="bulk_nurse").count() == 2
        )
        assert (
            patients_group.user_set.filter(username__startswith="bulk_patient").count()
            == 2
        )

        # Verify no cross-group assignments
        for user, profile in created_users:
            user_groups = list(user.groups.values_list("name", flat=True))
            assert len(user_groups) == 1  # Each user should be in exactly one group


@pytest.mark.django_db
@pytest.mark.system
class TestAdminInterfaceIntegration:
    """Test admin interface integration and workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.admin_site = AdminSite()

    def test_admin_registration_and_permissions(
        self, admin_user, doctor_user, sample_users
    ):
        """Test that admin registrations work and permissions are enforced."""
        # Test UserAdmin registration
        user_admin = UserAdmin(User, self.admin_site)
        profile_admin = UserProfileAdmin(UserProfile, self.admin_site)

        # Create mock requests
        class MockRequest:
            def __init__(self, user):
                self.user = user

        admin_request = MockRequest(admin_user)
        doctor_request = MockRequest(doctor_user)

        # Test UserAdmin permissions
        assert user_admin.has_module_permission(admin_request) is True
        assert user_admin.has_module_permission(doctor_request) is False

        # Test UserProfileAdmin permissions
        assert profile_admin.has_add_permission(admin_request) is True
        assert profile_admin.has_add_permission(doctor_request) is False

        assert profile_admin.has_delete_permission(admin_request) is True
        assert profile_admin.has_delete_permission(doctor_request) is False

    def test_admin_form_integration_with_fieldsets(self, admin_user):
        """Test admin form integration with dynamic fieldsets."""
        user_admin = UserAdmin(User, self.admin_site)

        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.POST = {}

        request = MockRequest(admin_user)

        # Test add fieldsets
        add_fieldsets = user_admin.get_fieldsets(request, obj=None)
        assert len(add_fieldsets) == 2
        assert "Role Assignment" in [fs[0] for fs in add_fieldsets]

        # Verify role fields are included
        role_fields = add_fieldsets[1][1]["fields"]
        assert "role" in role_fields
        assert "department" in role_fields
        assert "license_number" in role_fields
        assert "phone" in role_fields

    def test_profile_admin_fieldset_customization(
        self, admin_user, patient_user, doctor_user
    ):
        """Test UserProfileAdmin fieldset customization based on role."""
        profile_admin = UserProfileAdmin(UserProfile, self.admin_site)

        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.POST = {}

        admin_request = MockRequest(admin_user)

        # Test fieldsets for patient profile
        patient_fieldsets = profile_admin.get_fieldsets(
            admin_request, patient_user.profile
        )
        fieldset_names = [fs[0] for fs in patient_fieldsets]
        assert "Contact Information" in fieldset_names

        # Test fieldsets for doctor profile
        doctor_fieldsets = profile_admin.get_fieldsets(
            admin_request, doctor_user.profile
        )
        fieldset_names = [fs[0] for fs in doctor_fieldsets]
        assert "Professional Details" in fieldset_names


@pytest.mark.django_db
@pytest.mark.system
class TestSystemSecurity:
    """Test system-wide security and data isolation."""

    def test_user_data_isolation(self, sample_users):
        """Test that users can only access their own data appropriately."""
        profile_admin = UserProfileAdmin(UserProfile, AdminSite())

        # Create mock requests for different users
        class MockRequest:
            def __init__(self, user):
                self.user = user

        # Test patient isolation
        patient_request = MockRequest(sample_users["patient"])
        patient_queryset = profile_admin.get_queryset(patient_request)
        assert patient_queryset.count() == 1
        assert patient_queryset.first().user == sample_users["patient"]

        # Test doctor isolation
        doctor_request = MockRequest(sample_users["doctor"])
        doctor_queryset = profile_admin.get_queryset(doctor_request)
        assert doctor_queryset.count() == 1
        assert doctor_queryset.first().user == sample_users["doctor"]

        # Test admin sees all
        admin_request = MockRequest(sample_users["admin"])
        admin_queryset = profile_admin.get_queryset(admin_request)
        assert admin_queryset.count() >= 5  # Should see all sample users

    def test_role_based_group_integrity(self, create_groups):
        """Test that role-based group assignments maintain integrity across operations."""
        # Create users with various roles
        test_users = []
        roles = ["doctor", "nurse", "patient", "pharmacy", "admin"]

        for i, role in enumerate(roles):
            user = User.objects.create_user(
                username=f"integrity_test_{role}", password="testpass123"
            )

            profile_data = {"user": user, "role": role}
            if role in ["doctor", "nurse"]:
                profile_data["department"] = "Test Department"
            if role in ["doctor", "nurse", "pharmacy"]:
                profile_data["license_number"] = f"LIC{i:03d}"

            profile = UserProfile.objects.create(**profile_data)
            test_users.append((user, profile))

        # Verify each user is in exactly one group corresponding to their role
        role_to_group = {
            "patient": "Patients",
            "doctor": "Doctors",
            "nurse": "Nurses",
            "pharmacy": "Pharmacy",
            "admin": "Administrators",
        }

        for user, profile in test_users:
            user_groups = list(user.groups.values_list("name", flat=True))
            expected_group = role_to_group[profile.role]

            assert (
                len(user_groups) == 1
            ), f"User {user.username} should be in exactly one group"
            assert (
                expected_group in user_groups
            ), f"User {user.username} should be in {expected_group}"

        # Test role changes maintain integrity
        for user, profile in test_users:
            if profile.role == "patient":
                # Change patient to nurse
                profile.role = "nurse"
                profile.department = "Emergency"
                profile.license_number = "RN999"
                profile.save()

                user.refresh_from_db()
                new_groups = list(user.groups.values_list("name", flat=True))
                assert "Nurses" in new_groups
                assert "Patients" not in new_groups
                assert len(new_groups) == 1

    def test_system_handles_edge_cases(self, create_groups):
        """Test system robustness with edge cases."""
        # Test user without profile
        user_without_profile = User.objects.create_user(
            username="no_profile", password="testpass123"
        )

        # System should handle this gracefully
        profile_admin = UserProfileAdmin(UserProfile, AdminSite())

        class MockRequest:
            def __init__(self, user):
                self.user = user

        request = MockRequest(user_without_profile)

        # Should not crash and return empty queryset
        try:
            queryset = profile_admin.get_queryset(request)
            assert queryset.count() == 0
        except AttributeError:
            # Expected - user has no profile attribute
            pass

        # Test group cleanup when user is deleted
        test_user = User.objects.create_user(
            username="delete_test", password="testpass123"
        )
        test_profile = UserProfile.objects.create(
            user=test_user, role="doctor", department="Test", license_number="MD999"
        )

        # Verify group assignment
        test_user.refresh_from_db()
        assert test_user.groups.filter(name="Doctors").exists()

        # Delete user and verify cleanup
        user_id = test_user.id
        test_user.delete()

        # User should be removed from groups (cascade delete)
        doctors_group = Group.objects.get(name="Doctors")
        assert not doctors_group.user_set.filter(id=user_id).exists()
