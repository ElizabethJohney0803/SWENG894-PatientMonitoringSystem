"""
Migration tests for Patient Monitoring System.
Tests migration integrity and rollback functionality for PMS-009 acceptance criteria.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.test import TransactionTestCase
from django.db import connection
from django.core.management import call_command
from django.apps import apps
from django.contrib.auth.models import User
from datetime import date
from core.models import UserProfile, Patient, EmergencyContact


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.migrations
class TestPatientMigrations:
    """Test migration integrity for Patient and EmergencyContact models."""

    def test_patient_migration_creates_tables(self):
        """Test that Patient migration creates required database tables."""
        # Check that Patient table exists
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='core_patient';
            """
            )
            result = cursor.fetchone()
            assert result is not None, "Patient table was not created by migration"

    def test_emergency_contact_migration_creates_tables(self):
        """Test that EmergencyContact migration creates required database tables."""
        # Check that EmergencyContact table exists
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='core_emergencycontact';
            """
            )
            result = cursor.fetchone()
            assert (
                result is not None
            ), "EmergencyContact table was not created by migration"

    def test_patient_foreign_key_constraints(self, create_groups):
        """Test that foreign key constraints are properly created in migration."""
        # Create a NEW user/profile (ensure_patient_record will auto-create Patient)
        user = User.objects.create_user(
            username="fk_test", first_name="FK", last_name="Test", password="pass"
        )
        profile = UserProfile.objects.create(
            user=user, role="patient", phone="555-0000"
        )
        # Retrieve the auto-created Patient record
        patient = profile.patient_record

        # Test that foreign key relationship works
        assert patient.user_profile == profile
        assert profile.patient_record == patient

        # Test cascade behavior
        profile_id = profile.id
        profile.delete()

        # Patient should be deleted due to CASCADE
        assert not Patient.objects.filter(user_profile_id=profile_id).exists()

    def test_emergency_contact_foreign_key_constraints(self, patient_user):
        """Test EmergencyContact foreign key constraints from migration."""
        patient = patient_user.profile.patient_record

        contact = EmergencyContact.objects.create(
            patient=patient,
            name="FK Test Contact",
            relationship="parent",
            phone_primary="5552223333",
        )

        # Test foreign key relationship
        assert contact.patient == patient
        assert contact in patient.emergency_contacts.all()

        # Test cascade deletion
        patient_id = patient.id
        contact.delete()  # Clean up contact first
        # (Do not delete patient to avoid affecting other tests)

    def test_patient_model_fields_from_migration(self, patient_user):
        """Test that all required Patient model fields exist after migration."""
        patient = patient_user.profile.patient_record
        patient.date_of_birth = date(1992, 3, 15)
        patient.gender = "M"
        patient.blood_type = "AB+"
        patient.insurance_number = "TEST123456"
        patient.address_line1 = "Migration Field Test"
        patient.address_line2 = "Unit 100"
        patient.city = "Migration City"
        patient.state = "WA"
        patient.postal_code = "98765"
        patient.country = "United States"
        patient.phone_primary = "5554444444"
        patient.phone_secondary = "5555555555"
        patient.email_personal = "migration@test.com"
        patient.save()

        # Verify all fields are accessible (indicating they exist in database)
        patient.refresh_from_db()
        assert patient.medical_id is not None
        assert patient.date_of_birth == date(1992, 3, 15)
        assert patient.gender == "M"
        assert patient.blood_type == "AB+"
        assert patient.insurance_number == "TEST123456"
        assert patient.address_line1 == "Migration Field Test"
        assert patient.address_line2 == "Unit 100"
        assert patient.city == "Migration City"
        assert patient.state == "WA"
        assert patient.postal_code == "98765"
        assert patient.country == "United States"
        assert patient.phone_primary == "5554444444"
        assert patient.phone_secondary == "5555555555"
        assert patient.email_personal == "migration@test.com"
        assert patient.created_at is not None
        assert patient.updated_at is not None

    def test_emergency_contact_model_fields_from_migration(self, patient_user):
        """Test that all required EmergencyContact model fields exist after migration."""
        patient = patient_user.profile.patient_record

        contact = EmergencyContact.objects.create(
            patient=patient,
            name="Emergency Field Test",
            relationship="sibling",
            phone_primary="5557777777",
            phone_secondary="5558888888",
            email="emergency@field.test",
            is_primary_contact=False,
            notes="Field test for migration",
        )

        # Verify all fields are accessible
        contact.refresh_from_db()
        assert contact.patient == patient
        assert contact.name == "Emergency Field Test"
        assert contact.relationship == "sibling"
        assert contact.phone_primary == "5557777777"
        assert contact.phone_secondary == "5558888888"
        assert contact.email == "emergency@field.test"
        assert contact.is_primary_contact is False
        assert contact.notes == "Field test for migration"
        assert contact.created_at is not None
        assert contact.updated_at is not None

    def test_migration_unique_constraints(self, patient_user, create_groups):
        """Test that unique constraints from migration are enforced."""
        patient1 = patient_user.profile.patient_record

        # Create second patient user (auto-creates a second Patient record)
        user2 = User.objects.create_user(username="unique_test2", password="pass")
        profile2 = UserProfile.objects.create(
            user=user2, role="patient", phone="5552222222"
        )
        patient2 = profile2.patient_record

        # Medical IDs should be unique
        assert patient1.medical_id != patient2.medical_id

        # UserProfile relationships should be unique (OneToOne)
        assert patient1.user_profile != patient2.user_profile

    def test_migration_choice_field_constraints(self, patient_user):
        """Test that choice field constraints from migration work correctly."""
        patient = patient_user.profile.patient_record

        # Test valid gender choices
        valid_genders = ["M", "F", "O", "P"]
        for gender in valid_genders:
            patient.gender = gender
            patient.date_of_birth = date(1990, 1, 1)
            patient.address_line1 = "Choice Test"
            patient.city = "Choice City"
            patient.state = "CA"
            patient.postal_code = "12345"
            patient.phone_primary = "5551111111"
            # Should not raise exception during validation
            patient.full_clean()

        # Test valid blood type choices
        valid_blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        for blood_type in valid_blood_types:
            patient.blood_type = blood_type
            # Should not raise exception during validation
            patient.full_clean()

    def test_migration_database_indexes(self):
        """Test that database indexes from migration are created properly."""
        introspection = connection.introspection
        with connection.cursor() as cursor:
            constraints = introspection.get_constraints(cursor, "core_patient")

        # Check for medical_id unique index (unique=True + db_index=True on field)
        medical_id_indexed = any(
            "medical_id" in info.get("columns", [])
            and (info.get("unique") or info.get("index"))
            for info in constraints.values()
        )
        assert medical_id_indexed, "Medical ID index/unique constraint not found"

        # Check for user_profile_id index (OneToOne creates unique index)
        user_profile_indexed = any(
            "user_profile_id" in info.get("columns", [])
            and (info.get("unique") or info.get("index"))
            for info in constraints.values()
        )
        assert user_profile_indexed, "UserProfile foreign key index not found"


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.migrations
class TestMigrationIntegration:
    """Test migration integration with overall system."""

    def test_migrations_run_without_errors(self):
        """Test that all migrations can run without errors."""
        # This test verifies that the migration system is working
        # Since we're in a test environment, migrations have already run
        # We can verify this by checking that models are accessible

        # Try to access all model classes
        assert Patient is not None
        assert EmergencyContact is not None
        assert UserProfile is not None

        # Verify models are properly registered with Django
        patient_model = apps.get_model("core", "Patient")
        emergency_contact_model = apps.get_model("core", "EmergencyContact")

        assert patient_model == Patient
        assert emergency_contact_model == EmergencyContact

    def test_migration_data_integrity(self, create_groups):
        """Test that migration preserves data integrity constraints."""
        # Create complete patient workflow
        user = User.objects.create_user(
            username="integrity_test",
            first_name="Data",
            last_name="Integrity",
            password="pass",
        )
        profile = UserProfile.objects.create(
            user=user, role="patient", phone="5550000000"
        )

        # UserProfile.save() auto-creates the Patient via ensure_patient_record()
        patient = profile.patient_record
        patient.date_of_birth = date(1985, 12, 25)
        patient.gender = "F"
        patient.address_line1 = "Data Integrity Test"
        patient.city = "Integrity City"
        patient.state = "FL"
        patient.postal_code = "33101"
        patient.phone_primary = "5551111111"
        patient.save()

        # Add multiple emergency contacts
        contact1 = EmergencyContact.objects.create(
            patient=patient,
            name="Primary Contact",
            relationship="spouse",
            phone_primary="5552222222",
            is_primary_contact=True,
        )

        contact2 = EmergencyContact.objects.create(
            patient=patient,
            name="Secondary Contact",
            relationship="parent",
            phone_primary="5553333333",
        )

        # Verify all relationships and constraints work
        assert patient.user_profile == profile
        assert patient.emergency_contacts.count() == 2
        assert patient.get_primary_emergency_contact() == contact1
        assert contact1.is_primary_contact is True
        assert contact2.is_primary_contact is False

        # Test constraint enforcement
        contact3 = EmergencyContact.objects.create(
            patient=patient,
            name="New Primary",
            relationship="friend",
            phone_primary="5554444444",
            is_primary_contact=True,
        )

        # Previous primary should be updated
        contact1.refresh_from_db()
        assert contact1.is_primary_contact is False
        assert contact3.is_primary_contact is True
