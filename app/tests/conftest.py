# Test configuration and fixtures for Patient Monitoring System

import os
import django
import pytest
from django.conf import settings

# Configure Django settings before importing Django modules
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
)
django.setup()

from django.contrib.auth.models import User, Group
from django.test import TestCase
from core.models import UserProfile


@pytest.fixture
def create_groups():
    """Create all required groups for role-based testing."""
    groups = {
        "Patients": Group.objects.get_or_create(name="Patients")[0],
        "Doctors": Group.objects.get_or_create(name="Doctors")[0],
        "Nurses": Group.objects.get_or_create(name="Nurses")[0],
        "Pharmacy": Group.objects.get_or_create(name="Pharmacy")[0],
        "Administrators": Group.objects.get_or_create(name="Administrators")[0],
    }
    return groups


@pytest.fixture
def admin_user(create_groups):
    """Create an admin user with profile."""
    user = User.objects.create_user(
        username="admin_test",
        first_name="Admin",
        last_name="User",
        email="admin@hospital.com",
        password="testpass123",
        is_staff=True,
    )
    profile = UserProfile.objects.create(user=user, role="admin", phone="555-0001")
    return user


@pytest.fixture
def doctor_user(create_groups):
    """Create a doctor user with profile."""
    user = User.objects.create_user(
        username="doctor_test",
        first_name="John",
        last_name="Smith",
        email="doctor@hospital.com",
        password="testpass123",
        is_staff=True,
    )
    profile = UserProfile.objects.create(
        user=user,
        role="doctor",
        department="Cardiology",
        license_number="MD123456",
        phone="555-0002",
    )
    return user


@pytest.fixture
def nurse_user(create_groups):
    """Create a nurse user with profile."""
    user = User.objects.create_user(
        username="nurse_test",
        first_name="Jane",
        last_name="Doe",
        email="nurse@hospital.com",
        password="testpass123",
        is_staff=True,
    )
    profile = UserProfile.objects.create(
        user=user,
        role="nurse",
        department="Emergency",
        license_number="RN123456",
        phone="555-0003",
    )
    return user


@pytest.fixture
def patient_user(create_groups):
    """Create a patient user with profile."""
    user = User.objects.create_user(
        username="patient_test",
        first_name="Bob",
        last_name="Johnson",
        email="patient@email.com",
        password="testpass123",
    )
    profile = UserProfile.objects.create(user=user, role="patient", phone="555-0004")
    return user


@pytest.fixture
def pharmacy_user(create_groups):
    """Create a pharmacy user with profile."""
    user = User.objects.create_user(
        username="pharmacy_test",
        first_name="Mike",
        last_name="Wilson",
        email="pharmacy@hospital.com",
        password="testpass123",
        is_staff=True,
    )
    profile = UserProfile.objects.create(
        user=user, role="pharmacy", license_number="PH123456", phone="555-0005"
    )
    return user


@pytest.fixture
def sample_users(admin_user, doctor_user, nurse_user, patient_user, pharmacy_user):
    """Return all sample users."""
    return {
        "admin": admin_user,
        "doctor": doctor_user,
        "nurse": nurse_user,
        "patient": patient_user,
        "pharmacy": pharmacy_user,
    }


@pytest.fixture
def doctor_user_2(create_groups):
    """Create a second doctor user for multi-doctor tests."""
    user = User.objects.create_user(
        username="doctor2_test",
        first_name="Sarah",
        last_name="Johnson",
        email="doctor2@hospital.com",
        password="testpass123",
        is_staff=True,
    )
    profile = UserProfile.objects.create(
        user=user,
        role="doctor",
        department="Neurology",
        license_number="MD789012",
        phone="555-0006",
    )
    return user
