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
from datetime import date, timedelta
from core.models import UserProfile, Patient, EmergencyContact


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestPatientDoctorAssignment:
    """Test Patient-Doctor assignment functionality."""

    def test_patient_assigned_doctor_field_exists(self, patient_user, doctor_user):
        """Test that Patient model has assigned_doctor field."""
        patient = patient_user.profile.patient_record

        # Test field exists and is initially None
        assert hasattr(patient, "assigned_doctor")
        assert patient.assigned_doctor is None

        # Test assignment
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        # Verify assignment
        patient.refresh_from_db()
        assert patient.assigned_doctor == doctor_user.profile

    def test_patient_assigned_doctor_reverse_relationship(
        self, patient_user, doctor_user
    ):
        """Test reverse relationship from doctor to assigned patients."""
        patient = patient_user.profile.patient_record
        doctor_profile = doctor_user.profile

        # Initially no assigned patients
        assert doctor_profile.assigned_patients.count() == 0

        # Assign patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()

        # Test reverse relationship
        assert doctor_profile.assigned_patients.count() == 1
        assert patient in doctor_profile.assigned_patients.all()

    def test_patient_assigned_doctor_set_null_on_delete(
        self, patient_user, doctor_user
    ):
        """Test that deleting doctor sets assigned_doctor to NULL."""
        patient = patient_user.profile.patient_record
        doctor_profile = doctor_user.profile

        # Assign patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()

        # Delete doctor profile
        doctor_profile.delete()

        # Patient should still exist with assigned_doctor as None
        patient.refresh_from_db()
        assert patient.assigned_doctor is None

    def test_patient_assigned_doctor_validation(self, patient_user, admin_user):
        """Test validation that assigned_doctor must be a doctor."""
        patient = patient_user.profile.patient_record
        admin_profile = admin_user.profile

        # Try to assign non-doctor to patient
        patient.assigned_doctor = admin_profile

        # Should raise ValidationError on save
        with pytest.raises(
            ValidationError, match="Assigned doctor must have role='doctor'"
        ):
            patient.save()

    def test_doctor_utility_methods(self, doctor_user):
        """Test doctor utility methods for patient assignment."""
        doctor_profile = doctor_user.profile

        # Test get_assigned_patients for doctor
        assigned_patients = doctor_profile.get_assigned_patients()
        assert assigned_patients is not None
        assert assigned_patients.count() == 0

        # Test get_assigned_patients_count
        assert doctor_profile.get_assigned_patients_count() == 0

    def test_non_doctor_utility_methods(self, patient_user):
        """Test utility methods for non-doctor profiles."""
        patient_profile = patient_user.profile

        # Non-doctor should return None for get_assigned_patients
        assert patient_profile.get_assigned_patients() is None
        assert patient_profile.get_assigned_patients_count() == 0

    def test_can_assign_patients_property(self, admin_user, doctor_user, patient_user):
        """Test can_assign_patients property."""
        # Only admin can assign patients
        assert admin_user.profile.can_assign_patients is True
        assert doctor_user.profile.can_assign_patients is False
        assert patient_user.profile.can_assign_patients is False

    def test_multiple_patients_to_one_doctor(self, doctor_user):
        """Test that one doctor can have multiple assigned patients."""
        doctor_profile = doctor_user.profile

        # Create multiple patients
        patients = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"patient_multi_{i}",
                first_name=f"Patient{i}",
                last_name="Multi",
            )
            profile = UserProfile.objects.create(user=user, role="patient")
            patients.append(profile.patient_record)

        # Assign all patients to same doctor
        for patient in patients:
            patient.assigned_doctor = doctor_profile
            patient.save()

        # Verify all assignments
        assert doctor_profile.get_assigned_patients_count() == 3
        assigned = doctor_profile.get_assigned_patients()
        for patient in patients:
            assert patient in assigned

    def test_patient_can_be_unassigned(self, patient_user, doctor_user):
        """Test that patient assignment can be removed."""
        patient = patient_user.profile.patient_record
        doctor_profile = doctor_user.profile

        # Assign patient
        patient.assigned_doctor = doctor_profile
        patient.save()
        assert patient.assigned_doctor == doctor_profile

        # Unassign patient
        patient.assigned_doctor = None
        patient.save()

        # Verify unassignment
        patient.refresh_from_db()
        assert patient.assigned_doctor is None
        assert doctor_profile.get_assigned_patients_count() == 0


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


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestPatientModel:
    """Test Patient model functionality for PMS-009 acceptance criteria."""

    def test_patient_creation_with_required_fields(self, patient_user):
        """Test Patient model includes all required fields."""
        patient = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1990, 5, 15),
            gender="M",
            blood_type="O+",
            insurance_number="INS123456",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
            email_personal="patient@example.com",
        )

        # Verify all required fields are properly stored
        assert patient.user_profile == patient_user.profile
        assert patient.date_of_birth == date(1990, 5, 15)
        assert patient.gender == "M"
        assert patient.blood_type == "O+"
        assert patient.insurance_number == "INS123456"
        assert patient.address_line1 == "123 Main St"
        assert patient.city == "Anytown"
        assert patient.state == "CA"
        assert patient.postal_code == "12345"
        assert patient.phone_primary == "555-1234"
        assert patient.email_personal == "patient@example.com"
        assert patient.medical_id is not None

    def test_patient_medical_id_generation(self, patient_user):
        """Test automatic medical ID generation in correct format."""
        patient = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1985, 3, 20),
            gender="F",
            address_line1="456 Oak Ave",
            city="Somewhere",
            state="NY",
            postal_code="67890",
            phone_primary="555-5678",
        )

        # Medical ID should be auto-generated in format PMR-YYYY-NNNNNN
        assert patient.medical_id.startswith(f"PMR-{date.today().year}-")
        assert len(patient.medical_id) == 15  # PMR-YYYY-NNNNNN format

    def test_patient_medical_id_uniqueness(self, patient_user, create_groups):
        """Test that medical IDs are unique across patients."""
        # Create second patient user
        user2 = User.objects.create_user(
            username="patient2", first_name="Jane", last_name="Smith", password="pass"
        )
        profile2 = UserProfile.objects.create(
            user=user2, role="patient", phone="555-9999"
        )

        patient1 = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1990, 1, 1),
            gender="M",
            address_line1="123 Main St",
            city="City1",
            state="CA",
            postal_code="12345",
            phone_primary="555-1111",
        )

        patient2 = Patient.objects.create(
            user_profile=profile2,
            date_of_birth=date(1985, 2, 2),
            gender="F",
            address_line1="456 Oak Ave",
            city="City2",
            state="NY",
            postal_code="67890",
            phone_primary="555-2222",
        )

        # Medical IDs should be unique
        assert patient1.medical_id != patient2.medical_id

    def test_patient_date_of_birth_validation(self, patient_user):
        """Test date of birth validation rules."""
        # Future date should be invalid
        future_date = date.today() + timedelta(days=1)
        patient = Patient(
            user_profile=patient_user.profile,
            date_of_birth=future_date,
            gender="M",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
        )

        with pytest.raises(
            ValidationError, match="Date of birth cannot be in the future"
        ):
            patient.save()

        # Unrealistic age should be invalid
        ancient_date = date.today() - timedelta(days=365 * 150)  # 150 years ago
        patient.date_of_birth = ancient_date

        with pytest.raises(ValidationError, match="unrealistic age"):
            patient.save()

    def test_patient_age_calculation(self, patient_user):
        """Test age calculation property."""
        birth_date = date(1990, 5, 15)
        patient = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=birth_date,
            gender="M",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
        )

        # Calculate expected age
        today = date.today()
        expected_age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

        assert patient.age == expected_age

    def test_patient_address_formatting(self, patient_user):
        """Test full address property formatting."""
        patient = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1990, 1, 1),
            gender="F",
            address_line1="123 Main St",
            address_line2="Apt 4B",
            city="Anytown",
            state="CA",
            postal_code="12345",
            country="United States",
            phone_primary="555-1234",
        )

        expected_address = "123 Main St, Apt 4B, Anytown, CA, 12345, United States"
        assert patient.full_address == expected_address

        # Test without address line 2
        patient.address_line2 = None
        expected_address_no_line2 = "123 Main St, Anytown, CA, 12345, United States"
        assert patient.full_address == expected_address_no_line2

    def test_patient_phone_validation(self, patient_user):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = ["555-1234", "+1555123456", "5551234567"]

        for phone in valid_phones:
            patient = Patient(
                user_profile=patient_user.profile,
                date_of_birth=date(1990, 1, 1),
                gender="M",
                address_line1="123 Main St",
                city="Anytown",
                state="CA",
                postal_code="12345",
                phone_primary=phone,
            )
            # Should not raise exception
            patient.full_clean()

    def test_patient_userprofile_link_validation(self, create_groups):
        """Test that Patient can only link to UserProfile with role='patient'."""
        # Create a doctor user
        doctor_user = User.objects.create_user(username="doctor_test", password="pass")
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role="doctor",
            department="Cardiology",
            license_number="MD123",
        )

        patient = Patient(
            user_profile=doctor_profile,
            date_of_birth=date(1990, 1, 1),
            gender="M",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
        )

        with pytest.raises(
            ValidationError,
            match="Patient records can only be linked to UserProfiles with role='patient'",
        ):
            patient.save()

    def test_patient_string_representation(self, patient_user):
        """Test patient string representation includes medical ID and name."""
        patient = Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1990, 1, 1),
            gender="M",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
        )

        expected = f"{patient.medical_id} - {patient_user.get_full_name()}"
        assert str(patient) == expected


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestEmergencyContactModel:
    """Test EmergencyContact model functionality for PMS-009 acceptance criteria."""

    @pytest.fixture
    def sample_patient(self, patient_user):
        """Create a sample patient for emergency contact tests."""
        return Patient.objects.create(
            user_profile=patient_user.profile,
            date_of_birth=date(1990, 1, 1),
            gender="M",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            phone_primary="555-1234",
        )

    def test_emergency_contact_creation(self, sample_patient):
        """Test emergency contact creation with all required fields."""
        contact = EmergencyContact.objects.create(
            patient=sample_patient,
            name="John Emergency",
            relationship="spouse",
            phone_primary="555-9999",
            phone_secondary="555-8888",
            email="john@emergency.com",
            is_primary_contact=True,
            notes="Primary emergency contact",
        )

        assert contact.patient == sample_patient
        assert contact.name == "John Emergency"
        assert contact.relationship == "spouse"
        assert contact.phone_primary == "555-9999"
        assert contact.phone_secondary == "555-8888"
        assert contact.email == "john@emergency.com"
        assert contact.is_primary_contact is True
        assert contact.notes == "Primary emergency contact"

    def test_emergency_contact_patient_relationship(self, sample_patient):
        """Test ForeignKey relationship between EmergencyContact and Patient."""
        contact = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Jane Contact",
            relationship="parent",
            phone_primary="555-7777",
        )

        # Test forward relationship
        assert contact.patient == sample_patient

        # Test reverse relationship
        assert contact in sample_patient.emergency_contacts.all()

        # Test cascade deletion
        patient_id = sample_patient.id
        sample_patient.delete()
        assert not EmergencyContact.objects.filter(patient_id=patient_id).exists()

    def test_primary_contact_constraint(self, sample_patient):
        """Test that only one primary contact is allowed per patient."""
        # Create first primary contact
        contact1 = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Primary One",
            relationship="spouse",
            phone_primary="555-1111",
            is_primary_contact=True,
        )

        assert contact1.is_primary_contact is True

        # Create second primary contact
        contact2 = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Primary Two",
            relationship="parent",
            phone_primary="555-2222",
            is_primary_contact=True,
        )

        # First contact should no longer be primary
        contact1.refresh_from_db()
        assert contact1.is_primary_contact is False
        assert contact2.is_primary_contact is True

    def test_emergency_contact_ordering(self, sample_patient):
        """Test emergency contact ordering (primary first, then by name)."""
        # Create contacts in reverse alphabetical order
        contact_z = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Zoe Contact",
            relationship="friend",
            phone_primary="555-3333",
        )

        contact_a = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Alice Contact",
            relationship="parent",
            phone_primary="555-1111",
            is_primary_contact=True,
        )

        contact_b = EmergencyContact.objects.create(
            patient=sample_patient,
            name="Bob Contact",
            relationship="sibling",
            phone_primary="555-2222",
        )

        # Get ordered contacts
        ordered_contacts = list(sample_patient.emergency_contacts.all())

        # Primary contact should be first, then alphabetical
        assert ordered_contacts[0] == contact_a  # Primary first
        assert ordered_contacts[1] == contact_b  # Then alphabetical
        assert ordered_contacts[2] == contact_z

    def test_multiple_contacts_per_patient(self, sample_patient):
        """Test that multiple emergency contacts can be added to one patient."""
        contacts_data = [
            {
                "name": "Contact One",
                "relationship": "spouse",
                "phone_primary": "555-1111",
            },
            {
                "name": "Contact Two",
                "relationship": "parent",
                "phone_primary": "555-2222",
            },
            {
                "name": "Contact Three",
                "relationship": "sibling",
                "phone_primary": "555-3333",
            },
        ]

        for data in contacts_data:
            EmergencyContact.objects.create(patient=sample_patient, **data)

        # Verify all contacts are linked to patient
        assert sample_patient.emergency_contacts.count() == 3

        # Test utility methods
        all_contacts = sample_patient.get_emergency_contacts()
        assert len(all_contacts) == 3

        # No primary contact set yet
        assert sample_patient.get_primary_emergency_contact() is None

    def test_emergency_contact_phone_validation(self, sample_patient):
        """Test emergency contact phone number validation."""
        valid_phones = ["555-1234", "+1555123456", "5551234567"]

        for phone in valid_phones:
            contact = EmergencyContact(
                patient=sample_patient,
                name="Test Contact",
                relationship="friend",
                phone_primary=phone,
            )
            # Should not raise exception
            contact.full_clean()

    def test_emergency_contact_relationship_choices(self, sample_patient):
        """Test all valid relationship choices work."""
        relationships = [
            "spouse",
            "parent",
            "child",
            "sibling",
            "grandparent",
            "grandchild",
            "friend",
            "neighbor",
            "caregiver",
            "other",
        ]

        for i, relationship in enumerate(relationships):
            contact = EmergencyContact.objects.create(
                patient=sample_patient,
                name=f"Contact {i}",
                relationship=relationship,
                phone_primary=f"555-{1000+i}",
            )
            assert contact.relationship == relationship

    def test_emergency_contact_string_representation(self, sample_patient):
        """Test emergency contact string representation."""
        # Non-primary contact
        contact = EmergencyContact.objects.create(
            patient=sample_patient,
            name="John Doe",
            relationship="spouse",
            phone_primary="555-1234",
        )
        assert str(contact) == "John Doe - Spouse"

        # Primary contact
        contact.is_primary_contact = True
        contact.save()
        assert str(contact) == "John Doe - Spouse (Primary)"
