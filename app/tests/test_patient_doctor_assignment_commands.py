"""
Tests for Patient-Doctor assignment management commands.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from io import StringIO
from django.core.management import call_command
from django.contrib.auth.models import User
from core.models import UserProfile, Patient


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.management
class TestAssignPatientsCommand:
    """Test the assign_patients management command."""

    def test_list_doctors_command(self, create_groups):
        """Test listing all doctors."""
        # Create doctors
        doctor1_user = User.objects.create_user(
            username="doctor_cmd_1", password="pass"
        )
        doctor1_profile = UserProfile.objects.create(
            user=doctor1_user,
            role="doctor",
            department="Cardiology",
            license_number="DOC_CMD_1",
        )

        doctor2_user = User.objects.create_user(
            username="doctor_cmd_2", password="pass"
        )
        doctor2_profile = UserProfile.objects.create(
            user=doctor2_user,
            role="doctor",
            department="Neurology",
            license_number="DOC_CMD_2",
        )

        # Create a patient and assign to doctor1
        patient_user = User.objects.create_user(
            username="patient_cmd_1", password="pass"
        )
        patient_profile = UserProfile.objects.create(user=patient_user, role="patient")
        patient = patient_profile.patient_record
        patient.assigned_doctor = doctor1_profile
        patient.save()

        # Test command output
        out = StringIO()
        call_command("assign_patients", "--list-doctors", stdout=out)
        output = out.getvalue()

        assert "Found 2 doctors:" in output
        assert "doctor_cmd_1" in output
        assert "doctor_cmd_2" in output
        assert "Cardiology" in output
        assert "Neurology" in output
        assert "DOC_CMD_1" in output
        assert "DOC_CMD_2" in output
        assert "Assigned Patients: 1" in output  # doctor1 has 1 patient
        assert "Assigned Patients: 0" in output  # doctor2 has 0 patients

    def test_list_doctors_no_doctors(self):
        """Test listing doctors when none exist."""
        out = StringIO()
        call_command("assign_patients", "--list-doctors", stdout=out)
        output = out.getvalue()

        assert "No doctors found in the system." in output

    def test_list_unassigned_patients_command(self, create_groups):
        """Test listing unassigned patients."""
        # Create doctor
        doctor_user = User.objects.create_user(
            username="doctor_unassigned", password="pass"
        )
        doctor_profile = UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC_UNASSIGNED"
        )

        # Create patients - some assigned, some not
        patient1_user = User.objects.create_user(
            username="patient_unassigned_1", password="pass"
        )
        patient1_profile = UserProfile.objects.create(
            user=patient1_user, role="patient"
        )
        patient1 = patient1_profile.patient_record  # Will remain unassigned

        patient2_user = User.objects.create_user(
            username="patient_unassigned_2", password="pass"
        )
        patient2_profile = UserProfile.objects.create(
            user=patient2_user, role="patient"
        )
        patient2 = patient2_profile.patient_record
        patient2.assigned_doctor = doctor_profile  # Assigned
        patient2.save()

        # Test command output
        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()

        assert "Found 1 unassigned patients:" in output
        assert patient1.medical_id in output
        assert patient2.medical_id not in output
        assert "patient_unassigned_1" in output
        assert "patient_unassigned_2" not in output

    def test_list_unassigned_patients_all_assigned(self, create_groups):
        """Test listing unassigned patients when all are assigned."""
        # Create doctor and patient
        doctor_user = User.objects.create_user(
            username="doctor_all_assigned", password="pass"
        )
        doctor_profile = UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC_ALL_ASSIGNED"
        )

        patient_user = User.objects.create_user(
            username="patient_all_assigned", password="pass"
        )
        patient_profile = UserProfile.objects.create(user=patient_user, role="patient")
        patient = patient_profile.patient_record
        patient.assigned_doctor = doctor_profile
        patient.save()

        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()

        assert "All patients have assigned doctors." in output

    def test_assign_all_unassigned_command(self, create_groups):
        """Test assigning all unassigned patients to a doctor."""
        # Create doctor
        doctor_user = User.objects.create_user(
            username="doctor_assign_all", password="pass"
        )
        doctor_user.first_name = "Dr. Assign"
        doctor_user.last_name = "All"
        doctor_user.save()
        doctor_profile = UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC_ASSIGN_ALL"
        )

        # Create unassigned patients
        patients = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"patient_assign_all_{i}", password="pass"
            )
            profile = UserProfile.objects.create(user=user, role="patient")
            patients.append(profile.patient_record)

        # Verify initially unassigned
        for patient in patients:
            assert patient.assigned_doctor is None

        # Run command
        out = StringIO()
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "doctor_assign_all",
            stdout=out,
        )
        output = out.getvalue()

        # Verify output
        assert "Successfully assigned 3 patients to Dr. Dr. Assign All" in output
        assert "Dr. Dr. Assign All now has 3 assigned patients." in output

        # Verify assignments in database
        for patient in patients:
            patient.refresh_from_db()
            assert patient.assigned_doctor == doctor_profile

        assert doctor_profile.get_assigned_patients_count() == 3

    def test_assign_all_unassigned_no_unassigned(self, create_groups):
        """Test assign command when no unassigned patients exist."""
        # Create doctor
        doctor_user = User.objects.create_user(
            username="doctor_no_unassigned", password="pass"
        )
        doctor_profile = UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC_NO_UNASSIGNED"
        )

        out = StringIO()
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "doctor_no_unassigned",
            stdout=out,
        )
        output = out.getvalue()

        assert "No unassigned patients found." in output

    def test_assign_command_invalid_doctor(self):
        """Test assign command with invalid doctor username."""
        out = StringIO()
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "nonexistent_doctor",
            stdout=out,
        )
        output = out.getvalue()

        assert "Doctor with username nonexistent_doctor not found." in output

    def test_assign_command_non_doctor_user(self, create_groups):
        """Test assign command with user who is not a doctor."""
        # Create non-doctor user
        nurse_user = User.objects.create_user(
            username="nurse_not_doctor", password="pass"
        )
        nurse_profile = UserProfile.objects.create(
            user=nurse_user, role="nurse", license_number="NURSE_NOT_DOC"
        )

        out = StringIO()
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "nurse_not_doctor",
            stdout=out,
        )
        output = out.getvalue()

        assert "User nurse_not_doctor is not a doctor (role: nurse)" in output

    def test_assign_command_missing_doctor_username(self):
        """Test assign command without doctor username."""
        out = StringIO()
        call_command("assign_patients", "--assign-all-unassigned", stdout=out)
        output = out.getvalue()

        assert (
            "--doctor-username is required when using --assign-all-unassigned" in output
        )

    def test_command_no_options(self):
        """Test command without any options shows help message."""
        out = StringIO()
        call_command("assign_patients", stdout=out)
        output = out.getvalue()

        assert "Please specify an action. Use --help for available options." in output

    def test_command_integration_workflow(self, create_groups):
        """Test complete workflow using the management command."""
        # Create doctors
        doctor1_user = User.objects.create_user(
            username="doctor_workflow_1", password="pass"
        )
        doctor1_user.first_name = "Dr. Workflow"
        doctor1_user.last_name = "One"
        doctor1_user.save()
        doctor1_profile = UserProfile.objects.create(
            user=doctor1_user,
            role="doctor",
            department="Emergency",
            license_number="DOC_WF_1",
        )

        doctor2_user = User.objects.create_user(
            username="doctor_workflow_2", password="pass"
        )
        doctor2_user.first_name = "Dr. Workflow"
        doctor2_user.last_name = "Two"
        doctor2_user.save()
        doctor2_profile = UserProfile.objects.create(
            user=doctor2_user,
            role="doctor",
            department="Surgery",
            license_number="DOC_WF_2",
        )

        # Create patients
        patients = []
        for i in range(4):
            user = User.objects.create_user(
                username=f"patient_workflow_{i}", password="pass"
            )
            user.first_name = f"Patient{i}"
            user.last_name = "Workflow"
            user.save()
            profile = UserProfile.objects.create(user=user, role="patient")
            patients.append(profile.patient_record)

        # Step 1: List doctors (should show 2 with 0 patients each)
        out = StringIO()
        call_command("assign_patients", "--list-doctors", stdout=out)
        output = out.getvalue()
        assert "Found 2 doctors:" in output
        assert "Assigned Patients: 0" in output

        # Step 2: List unassigned patients (should show 4)
        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()
        assert "Found 4 unassigned patients:" in output

        # Step 3: Assign all to doctor1
        out = StringIO()
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "doctor_workflow_1",
            stdout=out,
        )
        output = out.getvalue()
        assert "Successfully assigned 4 patients to Dr. Dr. Workflow One" in output

        # Step 4: Verify assignment
        out = StringIO()
        call_command("assign_patients", "--list-doctors", stdout=out)
        output = out.getvalue()
        assert "Assigned Patients: 4" in output  # doctor1
        assert "Assigned Patients: 0" in output  # doctor2

        # Step 5: Verify no unassigned patients
        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()
        assert "All patients have assigned doctors." in output

        # Step 6: Verify database state
        assert doctor1_profile.get_assigned_patients_count() == 4
        assert doctor2_profile.get_assigned_patients_count() == 0

        for patient in patients:
            patient.refresh_from_db()
            assert patient.assigned_doctor == doctor1_profile


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.management
class TestAssignPatientsCommandIntegration:
    """Integration tests for assign_patients command with admin interface."""

    def test_command_effects_on_admin_interface(self, create_groups):
        """Test that command assignments are reflected in admin interface."""
        from core.admin import PatientAdmin
        from core.models import Patient
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        # Create doctor and patients
        doctor_user = User.objects.create_user(
            username="doctor_admin_int", password="pass"
        )
        doctor_profile = UserProfile.objects.create(
            user=doctor_user, role="doctor", license_number="DOC_ADMIN_INT"
        )

        patients = []
        for i in range(2):
            user = User.objects.create_user(
                username=f"patient_admin_int_{i}", password="pass"
            )
            profile = UserProfile.objects.create(user=user, role="patient")
            patients.append(profile.patient_record)

        # Use command to assign patients
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "doctor_admin_int",
        )

        # Test admin interface reflects assignments
        admin = PatientAdmin(Patient, AdminSite())
        factory = RequestFactory()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        # Doctor should now see both patients
        request = MockRequest(doctor_user)
        queryset = admin.get_queryset(request)
        assert queryset.count() == 2

        for patient in patients:
            assert patient in queryset
            assert admin.get_assigned_doctor(patient) == doctor_user.get_full_name()

    def test_command_with_mixed_assignment_states(self, create_groups):
        """Test command behavior with mixed assigned/unassigned patients."""
        # Create two doctors
        doctor1_user = User.objects.create_user(
            username="doctor_mixed_1", password="pass"
        )
        doctor1_profile = UserProfile.objects.create(
            user=doctor1_user, role="doctor", license_number="DOC_MIXED_1"
        )

        doctor2_user = User.objects.create_user(
            username="doctor_mixed_2", password="pass"
        )
        doctor2_user.first_name = "Dr. Mixed"
        doctor2_user.last_name = "Two"
        doctor2_user.save()
        doctor2_profile = UserProfile.objects.create(
            user=doctor2_user, role="doctor", license_number="DOC_MIXED_2"
        )

        # Create patients - some assigned, some not
        assigned_patients = []
        unassigned_patients = []

        for i in range(2):
            user = User.objects.create_user(
                username=f"patient_mixed_assigned_{i}", password="pass"
            )
            profile = UserProfile.objects.create(user=user, role="patient")
            patient = profile.patient_record
            patient.assigned_doctor = doctor1_profile  # Pre-assign to doctor1
            patient.save()
            assigned_patients.append(patient)

        for i in range(3):
            user = User.objects.create_user(
                username=f"patient_mixed_unassigned_{i}", password="pass"
            )
            profile = UserProfile.objects.create(user=user, role="patient")
            unassigned_patients.append(profile.patient_record)

        # Verify initial state
        assert doctor1_profile.get_assigned_patients_count() == 2
        assert doctor2_profile.get_assigned_patients_count() == 0

        # List unassigned should show only 3
        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()
        assert "Found 3 unassigned patients:" in output

        # Assign unassigned to doctor2
        call_command(
            "assign_patients",
            "--assign-all-unassigned",
            "--doctor-username",
            "doctor_mixed_2",
        )

        # Verify final state
        assert doctor1_profile.get_assigned_patients_count() == 2  # Unchanged
        assert (
            doctor2_profile.get_assigned_patients_count() == 3
        )  # Got the unassigned ones

        # All patients should now be assigned
        out = StringIO()
        call_command("assign_patients", "--list-unassigned", stdout=out)
        output = out.getvalue()
        assert "All patients have assigned doctors." in output
