"""
Unit tests for UserProfile model and related functionality.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from core.models import UserProfile


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestUserProfileModel:
    """Test UserProfile model functionality."""

    def test_user_profile_creation(self, create_groups):
        """Test basic user profile creation."""
        user = User.objects.create_user(username="test", password="pass")
        profile = UserProfile.objects.create(
            user=user,
            role="doctor",
            department="Cardiology",
            license_number="MD123",
            phone="555-1234",
        )

        assert profile.user == user
        assert profile.role == "doctor"
        assert profile.department == "Cardiology"
        assert profile.license_number == "MD123"
        assert profile.phone == "555-1234"

    def test_user_profile_str_representation(self, doctor_user):
        """Test string representation of user profile."""
        profile = doctor_user.profile
        expected = f"{doctor_user.get_full_name()} (Doctor)"
        assert str(profile) == expected

    def test_role_choices(self):
        """Test all valid role choices."""
        valid_roles = ["patient", "doctor", "nurse", "pharmacy", "admin"]
        for role in valid_roles:
            user = User.objects.create_user(username=f"user_{role}", password="pass")
            profile = UserProfile.objects.create(user=user, role=role)
            assert profile.role == role

    def test_is_medical_staff_property(self, sample_users):
        """Test is_medical_staff property for different roles."""
        assert sample_users["doctor"].profile.is_medical_staff is True
        assert sample_users["nurse"].profile.is_medical_staff is True
        assert sample_users["pharmacy"].profile.is_medical_staff is True
        assert sample_users["patient"].profile.is_medical_staff is False
        assert sample_users["admin"].profile.is_medical_staff is False

    def test_can_access_patient_records_property(self, sample_users):
        """Test can_access_patient_records property for different roles."""
        assert sample_users["doctor"].profile.can_access_patient_records is True
        assert sample_users["nurse"].profile.can_access_patient_records is True
        assert sample_users["admin"].profile.can_access_patient_records is True
        assert sample_users["pharmacy"].profile.can_access_patient_records is False
        assert sample_users["patient"].profile.can_access_patient_records is False

    def test_can_prescribe_medication_property(self, sample_users):
        """Test can_prescribe_medication property for different roles."""
        assert sample_users["doctor"].profile.can_prescribe_medication is True
        assert sample_users["admin"].profile.can_prescribe_medication is True
        assert sample_users["nurse"].profile.can_prescribe_medication is False
        assert sample_users["pharmacy"].profile.can_prescribe_medication is False
        assert sample_users["patient"].profile.can_prescribe_medication is False

    def test_can_manage_users_property(self, sample_users):
        """Test can_manage_users property for different roles."""
        assert sample_users["admin"].profile.can_manage_users is True
        assert sample_users["doctor"].profile.can_manage_users is False
        assert sample_users["nurse"].profile.can_manage_users is False
        assert sample_users["pharmacy"].profile.can_manage_users is False
        assert sample_users["patient"].profile.can_manage_users is False

    def test_is_complete_property_for_medical_staff(self, create_groups):
        """Test is_complete property for medical staff with required fields."""
        user = User.objects.create_user(username="test_doc", password="pass")

        # Incomplete profile - no license
        profile = UserProfile.objects.create(
            user=user, role="doctor", department="Cardiology"
        )
        assert profile.is_complete is False

        # Complete profile
        profile.license_number = "MD123"
        profile.save()
        assert profile.is_complete is True

    def test_is_complete_property_for_patient(self, patient_user):
        """Test is_complete property for patient (no license required)."""
        profile = patient_user.profile
        assert profile.is_complete is True

    def test_group_assignment_on_save(self, create_groups):
        """Test that users are assigned to correct groups on profile save."""
        user = User.objects.create_user(username="test_nurse", password="pass")
        profile = UserProfile.objects.create(
            user=user, role="nurse", department="Emergency", license_number="RN123"
        )

        # Check group assignment
        user.refresh_from_db()
        groups = list(user.groups.values_list("name", flat=True))
        assert "Nurses" in groups
        assert len(groups) == 1

    def test_group_reassignment_on_role_change(self, create_groups):
        """Test that groups change when role is updated."""
        user = User.objects.create_user(username="test_user", password="pass")
        profile = UserProfile.objects.create(user=user, role="patient")

        # Initial group assignment
        user.refresh_from_db()
        assert "Patients" in user.groups.values_list("name", flat=True)

        # Change role to doctor
        profile.role = "doctor"
        profile.department = "Surgery"
        profile.license_number = "MD999"
        profile.save()

        # Check new group assignment
        user.refresh_from_db()
        groups = list(user.groups.values_list("name", flat=True))
        assert "Doctors" in groups
        assert "Patients" not in groups
        assert len(groups) == 1

    def test_multiple_profiles_not_allowed(self, doctor_user):
        """Test that one user cannot have multiple profiles."""
        with pytest.raises(Exception):  # Should raise IntegrityError
            UserProfile.objects.create(user=doctor_user, role="admin")

    def test_assign_to_group_method(self, create_groups):
        """Test direct assign_to_group method call."""
        user = User.objects.create_user(username="test_assign", password="pass")
        profile = UserProfile.objects.create(user=user, role="pharmacy")

        # Manually call assign_to_group
        profile.assign_to_group()

        user.refresh_from_db()
        groups = list(user.groups.values_list("name", flat=True))
        assert "Pharmacy" in groups

    def test_missing_required_fields_validation(self, create_groups):
        """Test validation for missing required fields."""
        user = User.objects.create_user(username="test_validation", password="pass")

        # Test various incomplete medical staff profiles
        incomplete_profiles = [
            {"role": "doctor", "department": None, "license_number": "MD123"},
            {"role": "nurse", "department": "ICU", "license_number": None},
            {"role": "pharmacy", "license_number": None},
        ]

        for profile_data in incomplete_profiles:
            profile = UserProfile(user=user, **profile_data)
            missing = profile.get_missing_fields()
            assert len(missing) > 0

    def test_patient_no_required_fields(self, patient_user):
        """Test that patients have no missing required fields."""
        profile = patient_user.profile
        missing = profile.get_missing_fields()
        assert len(missing) == 0
