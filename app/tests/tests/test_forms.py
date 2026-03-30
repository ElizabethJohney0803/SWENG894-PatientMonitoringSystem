"""
Unit tests for admin forms and user creation functionality.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.test import TestCase, RequestFactory
from core.admin import CustomUserCreationForm
from core.models import UserProfile


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.forms
class TestCustomUserCreationForm:
    """Test CustomUserCreationForm functionality."""

    def test_form_valid_doctor_creation(self, create_groups):
        """Test creating a valid doctor through the form."""
        form_data = {
            "username": "test_doctor",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "doctor",
            "department": "Cardiology",
            "license_number": "MD123456",
            "phone": "555-1234",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        assert user.username == "test_doctor"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john.doe@hospital.com"

        # Check profile creation
        profile = user.profile
        assert profile.role == "doctor"
        assert profile.department == "Cardiology"
        assert profile.license_number == "MD123456"
        assert profile.phone == "555-1234"

        # Check group assignment
        groups = list(user.groups.values_list("name", flat=True))
        assert "Doctors" in groups

    def test_form_valid_nurse_creation(self, create_groups):
        """Test creating a valid nurse through the form."""
        form_data = {
            "username": "test_nurse",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "nurse",
            "department": "Emergency",
            "license_number": "RN123456",
            "phone": "555-5678",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        profile = user.profile
        assert profile.role == "nurse"
        assert profile.department == "Emergency"
        assert profile.license_number == "RN123456"

        # Check group assignment
        groups = list(user.groups.values_list("name", flat=True))
        assert "Nurses" in groups

    def test_form_valid_patient_creation(self, create_groups):
        """Test creating a valid patient through the form."""
        form_data = {
            "username": "test_patient",
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob.johnson@email.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "patient",
            "phone": "555-9876",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        profile = user.profile
        assert profile.role == "patient"
        assert profile.department == ""
        assert profile.license_number == ""
        assert profile.phone == "555-9876"

        # Check group assignment
        groups = list(user.groups.values_list("name", flat=True))
        assert "Patients" in groups

    def test_form_pharmacy_creation(self, create_groups):
        """Test creating a valid pharmacy user through the form."""
        form_data = {
            "username": "test_pharmacy",
            "first_name": "Mike",
            "last_name": "Wilson",
            "email": "mike.wilson@pharmacy.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "pharmacy",
            "license_number": "PH123456",
            "phone": "555-4321",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        profile = user.profile
        assert profile.role == "pharmacy"
        assert profile.license_number == "PH123456"

        # Check group assignment
        groups = list(user.groups.values_list("name", flat=True))
        assert "Pharmacy" in groups

    def test_form_admin_creation(self, create_groups):
        """Test creating a valid admin through the form."""
        form_data = {
            "username": "test_admin",
            "first_name": "Admin",
            "last_name": "User",
            "email": "admin@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "admin",
            "phone": "555-0000",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        profile = user.profile
        assert profile.role == "admin"

        # Check group assignment
        groups = list(user.groups.values_list("name", flat=True))
        assert "Administrators" in groups

    def test_form_validation_doctor_missing_license(self):
        """Test form validation when doctor is missing license number."""
        form_data = {
            "username": "test_doctor_invalid",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "doctor",
            "department": "Cardiology",
            "license_number": "",  # Missing required field
            "phone": "555-1234",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "license_number" in form.errors

    def test_form_validation_nurse_missing_department(self):
        """Test form validation when nurse is missing department."""
        form_data = {
            "username": "test_nurse_invalid",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "nurse",
            "department": "",  # Missing required field
            "license_number": "RN123456",
            "phone": "555-5678",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "department" in form.errors

    def test_form_validation_pharmacy_missing_license(self):
        """Test form validation when pharmacy user is missing license."""
        form_data = {
            "username": "test_pharmacy_invalid",
            "first_name": "Mike",
            "last_name": "Wilson",
            "email": "mike@pharmacy.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "pharmacy",
            "license_number": "",  # Missing required field
            "phone": "555-4321",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "license_number" in form.errors

    def test_form_validation_missing_role(self):
        """Test form validation when role is missing."""
        form_data = {
            "username": "test_no_role",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@hospital.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "",  # Missing required field
            "phone": "555-0000",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        # Should have validation error for missing role

    def test_patient_form_excludes_license_field(self, create_groups):
        """Test that license field handling for patients."""
        # This tests the conditional field removal logic
        form_data = {
            "username": "test_patient_license",
            "first_name": "Patient",
            "last_name": "User",
            "email": "patient@email.com",
            "password1": "complex_password_123",
            "password2": "complex_password_123",
            "role": "patient",
            "license_number": "SHOULD_NOT_BE_SET",  # Should be ignored
            "phone": "555-9999",
        }

        form = CustomUserCreationForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        user = form.save()
        profile = user.profile
        assert profile.role == "patient"
        assert profile.license_number == ""  # Should be empty for patients

    def test_form_password_validation(self):
        """Test password validation in the form."""
        form_data = {
            "username": "test_weak_password",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@hospital.com",
            "password1": "123",  # Weak password
            "password2": "123",
            "role": "patient",
            "phone": "555-0000",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        # Should have password validation errors

    def test_form_mismatched_passwords(self):
        """Test password mismatch validation."""
        form_data = {
            "username": "test_password_mismatch",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@hospital.com",
            "password1": "complex_password_123",
            "password2": "different_password_456",
            "role": "patient",
            "phone": "555-0000",
        }

        form = CustomUserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "password2" in form.errors
