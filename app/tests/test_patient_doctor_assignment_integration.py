"""
Integration tests for Patient-Doctor assignment functionality (PMS-010).
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings")

import django

django.setup()

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from core.models import UserProfile, Patient
from core.admin import PatientAdmin
from core.mixins import DoctorOnlyMixin
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.pms010
class TestPatientDoctorAssignmentIntegration:
    """Integration tests for Patient-Doctor assignment feature."""

    def setup_method(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_complete_assignment_workflow(self):
        """Test complete workflow from user creation to patient assignment."""
        # Create admin user
        admin_user = User.objects.create_user(
            username='admin_integration',
            first_name='Admin',
            last_name='User',
            password='testpass123'
        )
        admin_profile = UserProfile.objects.create(user=admin_user, role='admin')
        
        # Create doctor user
        doctor_user = User.objects.create_user(
            username='doctor_integration',
            first_name='Dr. John',
            last_name='Smith',
            password='testpass123'
        )
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            department='Cardiology',
            license_number='DOC12345'
        )
        
        # Create patient user
        patient_user = User.objects.create_user(
            username='patient_integration',
            first_name='Jane',
            last_name='Doe',
            password='testpass123'
        )
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Verify initial state
        assert patient.assigned_doctor is None
        assert doctor_profile.get_assigned_patients_count() == 0
        
        # Admin assigns patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()
        
        # Verify assignment
        patient.refresh_from_db()
        assert patient.assigned_doctor == doctor_profile
        assert doctor_profile.get_assigned_patients_count() == 1
        assert patient in doctor_profile.get_assigned_patients()

    def test_multiple_patients_single_doctor_workflow(self):
        """Test assigning multiple patients to single doctor."""
        # Create doctor
        doctor_user = User.objects.create_user(username='doctor_multi', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC456'
        )
        
        # Create multiple patients
        patients = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'patient_multi_{i}',
                first_name=f'Patient{i}',
                last_name='Multi'
            )
            profile = UserProfile.objects.create(user=user, role='patient')
            patients.append(profile.patient_record)
        
        # Assign all patients to doctor
        for patient in patients:
            patient.assigned_doctor = doctor_profile
            patient.save()
        
        # Verify assignments
        assert doctor_profile.get_assigned_patients_count() == 3
        for patient in patients:
            assert patient.assigned_doctor == doctor_profile
            assert patient in doctor_profile.get_assigned_patients()

    def test_patient_reassignment_workflow(self):
        """Test reassigning patient from one doctor to another."""
        # Create two doctors
        doctor1_user = User.objects.create_user(username='doctor1_reassign', password='pass')
        doctor1_profile = UserProfile.objects.create(
            user=doctor1_user,
            role='doctor',
            license_number='DOC111'
        )
        
        doctor2_user = User.objects.create_user(username='doctor2_reassign', password='pass')
        doctor2_profile = UserProfile.objects.create(
            user=doctor2_user,
            role='doctor',
            license_number='DOC222'
        )
        
        # Create patient
        patient_user = User.objects.create_user(username='patient_reassign', password='pass')
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Initial assignment to doctor1
        patient.assigned_doctor = doctor1_profile
        patient.save()
        
        # Verify initial assignment
        assert patient.assigned_doctor == doctor1_profile
        assert doctor1_profile.get_assigned_patients_count() == 1
        assert doctor2_profile.get_assigned_patients_count() == 0
        
        # Reassign to doctor2
        patient.assigned_doctor = doctor2_profile
        patient.save()
        
        # Verify reassignment
        patient.refresh_from_db()
        assert patient.assigned_doctor == doctor2_profile
        assert doctor1_profile.get_assigned_patients_count() == 0
        assert doctor2_profile.get_assigned_patients_count() == 1

    def test_doctor_deletion_patient_preservation(self):
        """Test that deleting doctor preserves patient data."""
        # Create doctor and patient
        doctor_user = User.objects.create_user(username='doctor_delete', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC789'
        )
        
        patient_user = User.objects.create_user(username='patient_preserve', password='pass')
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Assign patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()
        patient_id = patient.id
        
        # Delete doctor
        doctor_profile.delete()
        doctor_user.delete()
        
        # Verify patient still exists but assignment is None
        patient = Patient.objects.get(id=patient_id)
        assert patient.assigned_doctor is None
        assert patient.user_profile == patient_profile

    def test_admin_interface_integration(self):
        """Test admin interface integration with assignment functionality."""
        # Create users
        admin_user = User.objects.create_user(username='admin_interface', password='pass')
        admin_profile = UserProfile.objects.create(user=admin_user, role='admin')
        
        doctor_user = User.objects.create_user(username='doctor_interface', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC999'
        )
        
        patient_user = User.objects.create_user(username='patient_interface', password='pass')
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Test admin interface
        admin = PatientAdmin(Patient, self.admin_site)
        
        # Admin can see all patients
        request = self.factory.get('/')
        request.user = admin_user
        admin_queryset = admin.get_queryset(request)
        assert patient in admin_queryset
        
        # Doctor cannot see unassigned patient
        request.user = doctor_user
        doctor_queryset = admin.get_queryset(request)
        assert patient not in doctor_queryset
        
        # Assign patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()
        
        # Now doctor can see patient
        doctor_queryset = admin.get_queryset(request)
        assert patient in doctor_queryset
        
        # Test display methods
        assert admin.get_assigned_doctor(patient) == doctor_user.get_full_name()

    def test_permission_integration_across_roles(self):
        """Test permission integration across different user roles."""
        # Create users with different roles
        roles = ['admin', 'doctor', 'nurse', 'pharmacy', 'patient']
        users = {}
        profiles = {}
        
        for role in roles:
            user = User.objects.create_user(username=f'{role}_perm', password='pass')
            if role in ['doctor', 'nurse', 'pharmacy']:
                profile = UserProfile.objects.create(
                    user=user,
                    role=role,
                    license_number=f'{role.upper()}123'
                )
            else:
                profile = UserProfile.objects.create(user=user, role=role)
            users[role] = user
            profiles[role] = profile
        
        # Create patient and assign to doctor
        patient = profiles['patient'].patient_record
        patient.assigned_doctor = profiles['doctor']
        patient.save()
        
        admin = PatientAdmin(Patient, self.admin_site)
        
        # Test queryset filtering for each role
        for role, user in users.items():
            request = self.factory.get('/')
            request.user = user
            queryset = admin.get_queryset(request)
            
            if role == 'doctor':
                # Doctor sees only assigned patients
                assert patient in queryset
                assert queryset.count() == 1
            elif role in ['admin', 'nurse', 'pharmacy']:
                # These roles see all patients
                assert patient in queryset
            elif role == 'patient':
                # Patients see only their own record
                if patient.user_profile == profiles[role]:
                    assert patient in queryset
                else:
                    assert patient not in queryset

    def test_validation_and_constraints_integration(self):
        """Test model validation and constraints in real scenarios."""
        # Create users
        doctor_user = User.objects.create_user(username='doctor_valid', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC555'
        )
        
        admin_user = User.objects.create_user(username='admin_valid', password='pass')
        admin_profile = UserProfile.objects.create(user=admin_user, role='admin')
        
        patient_user = User.objects.create_user(username='patient_valid', password='pass')
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Valid assignment should work
        patient.assigned_doctor = doctor_profile
        patient.save()  # Should not raise exception
        
        # Invalid assignment should fail
        patient.assigned_doctor = admin_profile
        with pytest.raises(ValidationError, match=\"Assigned doctor must have role='doctor'\"):\n            patient.save()
        
        # Reset to valid state
        patient.assigned_doctor = doctor_profile
        patient.save()

    def test_bulk_operations_integration(self):
        \"\"\"Test bulk operations with patient-doctor assignments.\"\"\"
        # Create one doctor
        doctor_user = User.objects.create_user(username='doctor_bulk', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC_BULK'
        )
        
        # Create multiple unassigned patients
        patients = []
        for i in range(5):
            user = User.objects.create_user(username=f'patient_bulk_{i}', password='pass')
            profile = UserProfile.objects.create(user=user, role='patient')
            patients.append(profile.patient_record)
        
        # Verify all patients are initially unassigned
        unassigned_count = Patient.objects.filter(assigned_doctor__isnull=True).count()
        assert unassigned_count >= 5
        
        # Bulk assign all patients to doctor
        Patient.objects.filter(
            user_profile__user__username__startswith='patient_bulk_'
        ).update(assigned_doctor=doctor_profile)
        
        # Verify bulk assignment
        for patient in patients:
            patient.refresh_from_db()
            assert patient.assigned_doctor == doctor_profile
        
        assert doctor_profile.get_assigned_patients_count() == 5

    def test_emergency_contact_access_integration(self):
        \"\"\"Test that emergency contact access follows patient assignment rules.\"\"\"
        from core.models import EmergencyContact
        from core.mixins import DoctorOnlyMixin
        
        # Create doctor and patient
        doctor_user = User.objects.create_user(username='doctor_ec', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC_EC'
        )
        
        patient_user = User.objects.create_user(username='patient_ec', password='pass')
        patient_profile = UserProfile.objects.create(user=patient_user, role='patient')
        patient = patient_profile.patient_record
        
        # Create emergency contact
        emergency_contact = EmergencyContact.objects.create(
            patient=patient,
            name='John Emergency',
            relationship='spouse',
            phone_primary='555-0123'
        )
        
        # Test DoctorOnlyMixin filtering for emergency contacts
        class TestECAdmin(DoctorOnlyMixin):
            pass
        
        admin = TestECAdmin()
        request = self.factory.get('/')
        request.user = doctor_user
        
        ec_queryset = EmergencyContact.objects.all()
        
        # Doctor cannot see emergency contact when patient not assigned
        filtered_qs = admin.filter_queryset_by_role(request, ec_queryset, 'doctor')
        assert emergency_contact not in filtered_qs
        
        # Assign patient to doctor
        patient.assigned_doctor = doctor_profile
        patient.save()
        
        # Now doctor can see emergency contact
        filtered_qs = admin.filter_queryset_by_role(request, ec_queryset, 'doctor')
        assert emergency_contact in filtered_qs


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.performance
class TestPatientDoctorAssignmentPerformance:
    \"\"\"Performance tests for Patient-Doctor assignment functionality.\"\"\"

    def test_queryset_performance_with_many_patients(self):
        \"\"\"Test queryset performance with large number of patients.\"\"\"
        import time
        from django.test.utils import override_settings
        
        # Create doctor
        doctor_user = User.objects.create_user(username='doctor_perf', password='pass')
        doctor_profile = UserProfile.objects.create(
            user=doctor_user,
            role='doctor',
            license_number='DOC_PERF'
        )
        
        # Create many patients (some assigned, some not)
        assigned_patients = []
        unassigned_patients = []
        
        for i in range(50):  # Reduced for test efficiency
            user = User.objects.create_user(username=f'patient_perf_{i}', password='pass')
            profile = UserProfile.objects.create(user=user, role='patient')
            patient = profile.patient_record
            
            if i % 2 == 0:  # Assign every other patient
                patient.assigned_doctor = doctor_profile
                patient.save()
                assigned_patients.append(patient)
            else:
                unassigned_patients.append(patient)
        
        # Test query performance
        admin = PatientAdmin(Patient, AdminSite())
        request = RequestFactory().get('/')
        request.user = doctor_user
        
        start_time = time.time()
        queryset = admin.get_queryset(request)
        result_count = queryset.count()
        end_time = time.time()
        
        # Verify correctness
        assert result_count == len(assigned_patients)
        
        # Performance should be reasonable (under 1 second for 50 records)
        query_time = end_time - start_time
        assert query_time < 1.0, f\"Query took {query_time:.3f} seconds, expected < 1.0\"
        
        # Verify correct patients returned
        result_list = list(queryset)
        for patient in assigned_patients:
            assert patient in result_list
        for patient in unassigned_patients:
            assert patient not in result_list