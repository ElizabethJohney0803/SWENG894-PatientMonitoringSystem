"""
Tests for patient admin templates and custom dashboard functionality.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import get_template
from django.template import Context, RequestContext
from django.http import HttpRequest

from core.models import UserProfile, Patient, EmergencyContact


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.admin_templates
class TestPatientAdminTemplates:
    """Test custom admin templates for patient users."""

    def setup_method(self):
        """Set up test environment."""
        self.client = Client()

    def test_admin_index_template_exists(self):
        """Test that custom admin index template exists."""
        try:
            template = get_template("admin/index.html")
            assert template is not None
        except Exception:
            pytest.fail("Custom admin/index.html template should exist")

    def test_patient_dashboard_rendering(self, patient_user):
        """Test that patient dashboard renders correctly."""
        # Ensure user has staff access
        patient_user.is_staff = True
        patient_user.save()

        self.client.force_login(patient_user)
        response = self.client.get("/admin/")

        assert response.status_code == 200

        # Check for patient-specific content
        content = response.content.decode("utf-8")
        assert "Welcome" in content  # Welcome message
        assert "Patient Information" in content  # Patient section
        assert "View & Edit My Information" in content  # Action button

    def test_patient_changelist_template_rendering(self, patient_user):
        """Test that patient changelist renders with helpful context."""
        patient_user.is_staff = True
        patient_user.save()
        patient_user.profile.ensure_patient_record()

        self.client.force_login(patient_user)
        response = self.client.get("/admin/core/patient/")

        assert response.status_code == 200

        # Should contain patient help message
        assert "patient_help_message" in response.context

    def test_patient_change_form_template_rendering(self, patient_user):
        """Test that patient change form renders with helpful context."""
        patient_user.is_staff = True
        patient_user.save()
        patient_user.profile.ensure_patient_record()

        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        self.client.force_login(patient_user)
        response = self.client.get(f"/admin/core/patient/{patient_record.id}/change/")

        assert response.status_code == 200

        # Should contain patient help message
        assert "patient_help_message" in response.context

    def test_userprofile_admin_hidden_from_patients(self, patient_user):
        """Test that UserProfile admin is not accessible to patients."""
        patient_user.is_staff = True
        patient_user.save()

        self.client.force_login(patient_user)

        # Should get 403 Forbidden when trying to access UserProfile admin
        response = self.client.get("/admin/core/userprofile/")
        assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.patient_workflow
class TestPatientAdminWorkflow:
    """Test complete patient admin workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.client = Client()

    def test_complete_patient_login_workflow(self):
        """Test complete workflow from patient login to data editing."""
        # Create patient user
        user = User.objects.create_user(
            username="test_patient",
            password="testpass123",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )

        profile = UserProfile.objects.create(
            user=user, role="patient", phone="555-0123"
        )

        # Login
        login_success = self.client.login(
            username="test_patient", password="testpass123"
        )
        assert login_success is True

        # Access admin index - should see patient dashboard
        response = self.client.get("/admin/")
        assert response.status_code == 200
        assert (
            "Welcome, Jane Doe" in response.content.decode()
            or "Welcome, test_patient" in response.content.decode()
        )

        # Access patient changelist - should auto-create Patient record
        response = self.client.get("/admin/core/patient/")
        assert response.status_code == 200

        # Verify Patient record was created
        assert Patient.objects.filter(user_profile=profile).exists()
        patient_record = Patient.objects.get(user_profile=profile)

        # Access patient change form
        response = self.client.get(f"/admin/core/patient/{patient_record.id}/change/")
        assert response.status_code == 200

        # Update patient information
        update_data = {
            "user_profile": profile.id,
            "date_of_birth": "1990-05-15",
            "gender": "F",
            "blood_type": "A+",
            "phone_primary": "555-0198",
            "address_line1": "123 Main St",
            "city": "Test City",
            "state": "CA",
            "postal_code": "12345",
            "country": "USA",
            # Emergency contact inline data
            "emergencycontact_set-TOTAL_FORMS": "1",
            "emergencycontact_set-INITIAL_FORMS": "0",
            "emergencycontact_set-MIN_NUM_FORMS": "0",
            "emergencycontact_set-MAX_NUM_FORMS": "1000",
            "emergencycontact_set-0-name": "John Doe",
            "emergencycontact_set-0-relationship": "Spouse",
            "emergencycontact_set-0-phone_primary": "555-0199",
            "emergencycontact_set-0-email": "john@example.com",
            "emergencycontact_set-0-is_primary_contact": "on",
        }

        response = self.client.post(
            f"/admin/core/patient/{patient_record.id}/change/", update_data
        )

        # Should redirect on successful save
        assert response.status_code == 302

        # Verify data was saved
        patient_record.refresh_from_db()
        assert patient_record.phone_primary == "555-0198"
        assert patient_record.city == "Test City"

        # Verify emergency contact was created
        emergency_contacts = EmergencyContact.objects.filter(patient=patient_record)
        assert emergency_contacts.count() == 1
        assert emergency_contacts.first().name == "John Doe"

    def test_patient_cannot_access_other_admin_modules(self, patient_user):
        """Test that patients cannot access admin modules they shouldn't see."""
        patient_user.is_staff = True
        patient_user.save()

        self.client.force_login(patient_user)

        # Should not be able to access user management
        response = self.client.get("/admin/auth/user/")
        assert response.status_code == 403

        # Should not be able to access user profiles
        response = self.client.get("/admin/core/userprofile/")
        assert response.status_code == 403

    def test_patient_emergency_contact_inline_management(self, patient_user):
        """Test that patients can manage emergency contacts inline."""
        patient_user.is_staff = True
        patient_user.save()
        patient_user.profile.ensure_patient_record()

        patient_record = Patient.objects.get(user_profile=patient_user.profile)

        self.client.force_login(patient_user)

        # Access change form
        response = self.client.get(f"/admin/core/patient/{patient_record.id}/change/")
        assert response.status_code == 200

        # Check that emergency contact inline forms are present
        content = response.content.decode("utf-8")
        assert "emergencycontact_set" in content
        assert "Add another Emergency contact" in content


@pytest.mark.django_db
@pytest.mark.acceptance
class TestPatientAdminAcceptanceScenarios:
    """Test specific acceptance scenarios for patient admin access."""

    def setup_method(self):
        """Set up test environment."""
        self.client = Client()

    def test_scenario_new_patient_first_login(self):
        """Test scenario: New patient logs in for the first time."""
        # Create new patient user (as would be done by admin)
        user = User.objects.create_user(
            username="new_patient",
            password="welcome123",
            first_name="Alice",
            last_name="Smith",
        )

        profile = UserProfile.objects.create(user=user, role="patient")

        # Login for first time
        self.client.login(username="new_patient", password="welcome123")

        # Visit admin index - should see welcome dashboard
        response = self.client.get("/admin/")
        assert response.status_code == 200
        assert "Welcome, Alice Smith" in response.content.decode()

        # Click on "View & Edit My Information" - should auto-create Patient record
        response = self.client.get("/admin/core/patient/")
        assert response.status_code == 200

        # Patient record should be auto-created
        assert Patient.objects.filter(user_profile=profile).exists()

        # Should see their empty patient record ready to fill out
        patient_record = Patient.objects.get(user_profile=profile)
        response = self.client.get(f"/admin/core/patient/{patient_record.id}/change/")
        assert response.status_code == 200

    def test_scenario_patient_updates_emergency_contact(self):
        """Test scenario: Patient updates their emergency contact information."""
        user = User.objects.create_user(username="patient", password="pass")
        profile = UserProfile.objects.create(user=user, role="patient")
        profile.ensure_patient_record()
        patient_record = Patient.objects.get(user_profile=profile)

        # Create initial emergency contact
        emergency_contact = EmergencyContact.objects.create(
            patient=patient_record,
            name="Old Contact",
            relationship="Friend",
            phone_primary="555-0100",
        )

        self.client.force_login(user)

        # Update emergency contact
        update_data = {
            "user_profile": profile.id,
            "emergencycontact_set-TOTAL_FORMS": "1",
            "emergencycontact_set-INITIAL_FORMS": "1",
            "emergencycontact_set-MIN_NUM_FORMS": "0",
            "emergencycontact_set-MAX_NUM_FORMS": "1000",
            f"emergencycontact_set-0-id": emergency_contact.id,
            "emergencycontact_set-0-name": "Updated Contact",
            "emergencycontact_set-0-relationship": "Spouse",
            "emergencycontact_set-0-phone_primary": "555-0200",
            "emergencycontact_set-0-email": "updated@example.com",
            "emergencycontact_set-0-is_primary_contact": "on",
        }

        response = self.client.post(
            f"/admin/core/patient/{patient_record.id}/change/", update_data
        )
        assert response.status_code == 302  # Successful save

        # Verify update
        emergency_contact.refresh_from_db()
        assert emergency_contact.name == "Updated Contact"
        assert emergency_contact.relationship == "Spouse"
        assert emergency_contact.phone_primary == "555-0200"

    def test_scenario_patient_tries_to_access_other_patient_data(self):
        """Test scenario: Patient tries to access another patient's data (should be denied)."""
        # Create two patients
        patient1 = User.objects.create_user(username="patient1", password="pass")
        profile1 = UserProfile.objects.create(user=patient1, role="patient")
        profile1.ensure_patient_record()
        record1 = Patient.objects.get(user_profile=profile1)

        patient2 = User.objects.create_user(username="patient2", password="pass")
        profile2 = UserProfile.objects.create(user=patient2, role="patient")
        profile2.ensure_patient_record()
        record2 = Patient.objects.get(user_profile=profile2)

        # Login as patient1
        self.client.force_login(patient1)

        # Try to access patient2's record - should be denied
        response = self.client.get(f"/admin/core/patient/{record2.id}/change/")
        assert response.status_code == 403  # Forbidden

        # Patient1 should only see their own record in changelist
        response = self.client.get("/admin/core/patient/")
        assert response.status_code == 200

        # Check that only patient1's record is in the queryset
        content = response.content.decode("utf-8")
        assert str(record1.medical_id) in content
        assert str(record2.medical_id) not in content
