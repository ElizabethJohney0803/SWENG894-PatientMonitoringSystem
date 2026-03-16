"""
Tests for the Medication model, Patient medical-history fields,
MedicationAdmin, and PatientAdmin integration.

FR coverage:
  FR-D-4   Doctor can add/edit patient diagnoses, procedures, visit notes
  FR-D-5   Doctor can view current and past medications of assigned patients
  FR-N-2   Nurse can view current medications of assigned patients (read-only)
  FR-Ph-1  Pharmacy can view medication orders for patients
  FR-Ph-3  Pharmacy can view allergy information
  FR-AA-2  Role-based access control
  FR-AA-3  No unauthorised access
"""

import pytest
from datetime import date, timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory

from core.admin import MedicationAdmin, PatientAdmin
from core.models import Medication, Patient, UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TWO_WEEKS_AGO = TODAY - timedelta(days=14)


def _make_patient_user(username, first="Pat", last="Test"):
    """Create User + patient UserProfile (auto-creates Patient via signal)."""
    user = User.objects.create_user(
        username=username, first_name=first, last_name=last, password="pass"
    )
    UserProfile.objects.create(user=user, role="patient")
    return user


def _make_doctor_user(username, first="Doc", last="Smith"):
    user = User.objects.create_user(
        username=username,
        first_name=first,
        last_name=last,
        password="pass",
        is_staff=True,
    )
    UserProfile.objects.create(
        user=user, role="doctor", license_number="MD-TEST", phone="555-0099"
    )
    return user


def _make_med(patient, doctor=None, name="Metformin", status="current", **kwargs):
    defaults = dict(
        dosage="500 mg",
        frequency="Twice daily",
        start_date=TWO_WEEKS_AGO,
        status=status,
    )
    defaults.update(kwargs)
    return Medication.objects.create(
        patient=patient,
        prescribing_doctor=doctor.profile if doctor else None,
        medication_name=name,
        **defaults,
    )


def _make_request(factory, user):
    req = factory.get("/")
    req.user = user
    return req


# ─────────────────────────────────────────────────────────────────────────────
# 1. Medication model — fields and defaults
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestMedicationModelFields:
    """Medication model basic field behaviour."""

    def test_create_minimal_medication(self):
        """Medication with required fields only saves successfully."""
        doc = _make_doctor_user("doc_min")
        pat_user = _make_patient_user("pat_min")
        patient = pat_user.profile.patient_record
        med = _make_med(patient, doctor=doc)
        assert med.pk is not None

    def test_default_status_is_current(self):
        pat_user = _make_patient_user("pat_status_def")
        patient = pat_user.profile.patient_record
        med = Medication.objects.create(
            patient=patient,
            medication_name="Aspirin",
            dosage="100 mg",
            frequency="Daily",
            start_date=YESTERDAY,
        )
        assert med.status == "current"

    def test_status_choices(self):
        choices = dict(Medication.STATUS_CHOICES)
        assert "current" in choices
        assert "past" in choices

    def test_end_date_nullable(self):
        pat_user = _make_patient_user("pat_end_null")
        patient = pat_user.profile.patient_record
        med = Medication.objects.create(
            patient=patient,
            medication_name="Lisinopril",
            dosage="10 mg",
            frequency="Once daily",
            start_date=YESTERDAY,
        )
        assert med.end_date is None

    def test_prescribing_doctor_nullable(self):
        pat_user = _make_patient_user("pat_doc_null")
        patient = pat_user.profile.patient_record
        med = _make_med(patient, doctor=None)
        assert med.prescribing_doctor is None

    def test_notes_defaults_to_empty(self):
        pat_user = _make_patient_user("pat_notes")
        patient = pat_user.profile.patient_record
        med = _make_med(patient)
        assert med.notes == ""

    def test_str_representation(self):
        pat_user = _make_patient_user("pat_str")
        patient = pat_user.profile.patient_record
        med = _make_med(patient, name="Atorvastatin", status="current")
        assert "Atorvastatin" in str(med)
        assert "Current" in str(med) or "current" in str(med).lower()

    def test_str_past_status(self):
        pat_user = _make_patient_user("pat_str_past")
        patient = pat_user.profile.patient_record
        med = _make_med(patient, name="Penicillin", status="past",
                        end_date=YESTERDAY)
        assert "Penicillin" in str(med)

    def test_ordering_current_before_past(self):
        """Meta.ordering: 'current' sorts before 'past'."""
        doc = _make_doctor_user("doc_ord")
        pat_user = _make_patient_user("pat_ord")
        patient = pat_user.profile.patient_record
        patient.assigned_doctor = doc.profile
        patient.save()
        _make_med(patient, doctor=doc, name="PastMed", status="past",
                  end_date=YESTERDAY)
        _make_med(patient, doctor=doc, name="CurrentMed", status="current")
        meds = list(Medication.objects.filter(patient=patient))
        assert meds[0].status == "current"
        assert meds[1].status == "past"

    def test_ordering_by_start_date_within_status(self):
        """Within same status, newer start_date comes first."""
        pat_user = _make_patient_user("pat_date_ord")
        patient = pat_user.profile.patient_record
        older = _make_med(patient, name="Older",
                          start_date=TODAY - timedelta(days=30))
        newer = _make_med(patient, name="Newer",
                          start_date=TODAY - timedelta(days=5))
        meds = list(Medication.objects.filter(patient=patient))
        assert meds[0].medication_name == "Newer"
        assert meds[1].medication_name == "Older"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Medication model — clean() validation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestMedicationModelValidation:
    """Medication.clean() raises ValidationError on invalid data."""

    def test_end_date_before_start_raises(self):
        pat_user = _make_patient_user("pat_val1")
        patient = pat_user.profile.patient_record
        med = Medication(
            patient=patient,
            medication_name="Bad",
            dosage="5 mg",
            frequency="Daily",
            start_date=TODAY,
            end_date=YESTERDAY,
        )
        with pytest.raises(ValidationError, match="End date"):
            med.clean()

    def test_end_date_equal_to_start_is_valid(self):
        pat_user = _make_patient_user("pat_val2")
        patient = pat_user.profile.patient_record
        med = Medication(
            patient=patient,
            medication_name="OK",
            dosage="5 mg",
            frequency="Daily",
            start_date=TODAY,
            end_date=TODAY,
        )
        med.clean()  # should not raise

    def test_end_date_after_start_is_valid(self):
        pat_user = _make_patient_user("pat_val3")
        patient = pat_user.profile.patient_record
        med = Medication(
            patient=patient,
            medication_name="OK2",
            dosage="5 mg",
            frequency="Daily",
            start_date=YESTERDAY,
            end_date=TODAY,
        )
        med.clean()  # should not raise

    def test_no_end_date_is_valid(self):
        pat_user = _make_patient_user("pat_val4")
        patient = pat_user.profile.patient_record
        med = Medication(
            patient=patient,
            medication_name="NoEnd",
            dosage="5 mg",
            frequency="Daily",
            start_date=TODAY,
            end_date=None,
        )
        med.clean()  # should not raise

    def test_non_doctor_prescriber_raises(self):
        """prescribing_doctor must have role='doctor'."""
        nurse_user = User.objects.create_user(
            username="nurse_val_test", password="pass", is_staff=True
        )
        nurse_profile = UserProfile.objects.create(
            user=nurse_user, role="nurse", license_number="RN-T99"
        )
        pat_user = _make_patient_user("pat_val5")
        patient = pat_user.profile.patient_record
        med = Medication(
            patient=patient,
            prescribing_doctor=nurse_profile,
            medication_name="Conflict",
            dosage="5 mg",
            frequency="Daily",
            start_date=TODAY,
        )
        with pytest.raises(ValidationError, match="role='doctor'"):
            med.clean()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Patient model — medical history TextField fields (FR-D-4)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestPatientMedicalHistoryFields:
    """The five new medical-history TextFields on the Patient model."""

    def test_all_fields_default_to_empty(self):
        pat_user = _make_patient_user("pat_hist_def")
        patient = pat_user.profile.patient_record
        for field in (
            "diagnoses", "procedures", "visit_notes",
            "allergies", "chronic_conditions",
        ):
            assert getattr(patient, field) == ""

    def test_diagnoses_saves_and_retrieves(self):
        pat_user = _make_patient_user("pat_diag")
        patient = pat_user.profile.patient_record
        patient.diagnoses = "Type 2 Diabetes\nHypertension"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert "Type 2 Diabetes" in fresh.diagnoses

    def test_procedures_saves_and_retrieves(self):
        pat_user = _make_patient_user("pat_proc")
        patient = pat_user.profile.patient_record
        patient.procedures = "Appendectomy 2020-01-15"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert "Appendectomy" in fresh.procedures

    def test_visit_notes_saves_and_retrieves(self):
        pat_user = _make_patient_user("pat_vnotes")
        patient = pat_user.profile.patient_record
        patient.visit_notes = "Follow-up in 3 months"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert "Follow-up" in fresh.visit_notes

    def test_allergies_saves_and_retrieves(self):
        pat_user = _make_patient_user("pat_allergy")
        patient = pat_user.profile.patient_record
        patient.allergies = "Penicillin, Peanuts"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert "Penicillin" in fresh.allergies

    def test_chronic_conditions_saves_and_retrieves(self):
        pat_user = _make_patient_user("pat_chronic")
        patient = pat_user.profile.patient_record
        patient.chronic_conditions = "Asthma"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert "Asthma" in fresh.chronic_conditions

    def test_all_five_fields_persist_together(self):
        pat_user = _make_patient_user("pat_all5")
        patient = pat_user.profile.patient_record
        patient.diagnoses = "DX"
        patient.procedures = "PR"
        patient.visit_notes = "VN"
        patient.allergies = "AL"
        patient.chronic_conditions = "CC"
        patient.save()
        fresh = Patient.objects.get(pk=patient.pk)
        assert fresh.diagnoses == "DX"
        assert fresh.procedures == "PR"
        assert fresh.visit_notes == "VN"
        assert fresh.allergies == "AL"
        assert fresh.chronic_conditions == "CC"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Medication — FK relationships
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestMedicationRelationships:
    """FK cascade and reverse-manager behaviour."""

    def test_patient_cascade_delete(self):
        """Deleting a Patient cascades to Medication records."""
        doc = _make_doctor_user("doc_casc")
        pat_user = _make_patient_user("pat_casc")
        patient = pat_user.profile.patient_record
        _make_med(patient, doctor=doc)
        patient_pk = patient.pk
        # Delete patient user (cascades to Patient via UserProfile)
        pat_user.delete()
        assert Medication.objects.filter(
            patient__pk=patient_pk
        ).count() == 0

    def test_doctor_delete_sets_null(self):
        """Deleting a prescribing doctor sets prescribing_doctor to NULL."""
        doc = _make_doctor_user("doc_null_del")
        pat_user = _make_patient_user("pat_null_del")
        patient = pat_user.profile.patient_record
        med = _make_med(patient, doctor=doc)
        doc.delete()
        med.refresh_from_db()
        assert med.prescribing_doctor is None

    def test_patient_reverse_manager(self):
        """patient.medications reverse manager returns correct queryset."""
        pat_user = _make_patient_user("pat_rev")
        patient = pat_user.profile.patient_record
        _make_med(patient, name="DrugA")
        _make_med(patient, name="DrugB")
        assert patient.medications.count() == 2

    def test_doctor_reverse_manager(self):
        """doctor_profile.prescribed_medications returns correct queryset."""
        doc = _make_doctor_user("doc_rev")
        pat_user = _make_patient_user("pat_rev_doc")
        patient = pat_user.profile.patient_record
        _make_med(patient, doctor=doc, name="DocDrug")
        assert doc.profile.prescribed_medications.count() == 1

    def test_multiple_patients_medications_isolated(self):
        """Medications for one patient are not visible on another's manager."""
        pat1 = _make_patient_user("pat_iso1").profile.patient_record
        pat2 = _make_patient_user("pat_iso2").profile.patient_record
        _make_med(pat1, name="OnlyForPat1")
        assert pat2.medications.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. MedicationAdmin — queryset scoping per role (FR-D-5/FR-N-2/FR-Ph-1)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.admin
class TestMedicationAdminQueryset:
    """MedicationAdmin.get_queryset() scopes by role correctly."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = AdminSite()
        self.ma = MedicationAdmin(Medication, self.site)
        self.factory = RequestFactory()

        self.doc = _make_doctor_user("doc_qs")
        self.doc2 = _make_doctor_user("doc_qs2", first="Other", last="Doc")

        self.pat_assigned = _make_patient_user(
            "pat_qs_assigned"
        ).profile.patient_record
        self.pat_assigned.assigned_doctor = self.doc.profile
        self.pat_assigned.save()

        self.pat_unassigned = _make_patient_user(
            "pat_qs_unassigned"
        ).profile.patient_record
        # pat_unassigned belongs to doc2
        self.pat_unassigned.assigned_doctor = self.doc2.profile
        self.pat_unassigned.save()

        self.med_assigned = _make_med(
            self.pat_assigned, doctor=self.doc, name="AssignedDrug"
        )
        self.med_unassigned = _make_med(
            self.pat_unassigned, doctor=self.doc2, name="UnassignedDrug"
        )

        # Admin user
        self.admin = User.objects.create_user(
            username="admin_qs_med",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )

        # Nurse user
        self.nurse = User.objects.create_user(
            username="nurse_qs_med", password="pass", is_staff=True
        )
        UserProfile.objects.create(
            user=self.nurse, role="nurse", license_number="RN-QS"
        )

        # Pharmacy user
        self.pharm = User.objects.create_user(
            username="pharm_qs_med", password="pass", is_staff=True
        )
        UserProfile.objects.create(
            user=self.pharm, role="pharmacy", license_number="PH-QS"
        )

        # Patient user (own patient)
        self.patient_user = _make_patient_user("pat_qs_own")
        _make_med(
            self.patient_user.profile.patient_record, name="OwnDrug"
        )

    def test_superuser_sees_all(self):
        req = _make_request(self.factory, self.admin)
        qs = self.ma.get_queryset(req)
        pks = list(qs.values_list("pk", flat=True))
        assert self.med_assigned.pk in pks
        assert self.med_unassigned.pk in pks

    def test_doctor_sees_only_assigned_patient_meds(self):
        req = _make_request(self.factory, self.doc)
        qs = self.ma.get_queryset(req)
        pks = list(qs.values_list("pk", flat=True))
        assert self.med_assigned.pk in pks
        assert self.med_unassigned.pk not in pks

    def test_doctor_sees_no_meds_if_no_assigned_patients(self):
        lone_doc = _make_doctor_user("doc_lone")
        req = _make_request(self.factory, lone_doc)
        qs = self.ma.get_queryset(req)
        assert qs.count() == 0

    def test_nurse_sees_all_meds(self):
        req = _make_request(self.factory, self.nurse)
        qs = self.ma.get_queryset(req)
        pks = list(qs.values_list("pk", flat=True))
        assert self.med_assigned.pk in pks
        assert self.med_unassigned.pk in pks

    def test_pharmacy_sees_all_meds(self):
        req = _make_request(self.factory, self.pharm)
        qs = self.ma.get_queryset(req)
        pks = list(qs.values_list("pk", flat=True))
        assert self.med_assigned.pk in pks
        assert self.med_unassigned.pk in pks

    def test_patient_sees_only_own_meds(self):
        req = _make_request(self.factory, self.patient_user)
        qs = self.ma.get_queryset(req)
        names = list(qs.values_list("medication_name", flat=True))
        assert "OwnDrug" in names
        assert "AssignedDrug" not in names

    def test_user_without_profile_sees_nothing(self):
        bare = User.objects.create_user(
            username="bare_qs_med", password="pass"
        )
        req = _make_request(self.factory, bare)
        assert self.ma.get_queryset(req).count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. MedicationAdmin — permissions per role (FR-AA-2 / FR-AA-3)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.admin
class TestMedicationAdminPermissions:
    """MedicationAdmin add / change / delete / view permissions per role."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = AdminSite()
        self.ma = MedicationAdmin(Medication, self.site)
        self.factory = RequestFactory()

        self.superuser = User.objects.create_user(
            "perm_su_med", password="pass",
            is_staff=True, is_superuser=True
        )

        def _staff(username, role, lic="X-00"):
            u = User.objects.create_user(
                username, password="pass", is_staff=True
            )
            UserProfile.objects.create(user=u, role=role, license_number=lic)
            return u

        self.admin_u = _staff("perm_admin_med", "admin", "A-00")
        self.doctor_u = _staff("perm_doc_med", "doctor", "D-00")
        self.nurse_u = _staff("perm_nurse_med", "nurse", "N-00")
        self.pharm_u = _staff("perm_pharm_med", "pharmacy", "P-00")
        self.patient_u = _make_patient_user("perm_pat_med")

        # A medication for object-level tests
        pat = _make_patient_user("perm_obj_pat").profile.patient_record
        pat.assigned_doctor = self.doctor_u.profile
        pat.save()
        self.med_obj = _make_med(pat, doctor=self.doctor_u)

        pat2 = _make_patient_user("perm_obj_pat2").profile.patient_record
        self.med_other = _make_med(pat2, name="OtherDoc")

    # add_permission
    def test_superuser_can_add(self):
        req = _make_request(self.factory, self.superuser)
        assert self.ma.has_add_permission(req)

    def test_admin_can_add(self):
        req = _make_request(self.factory, self.admin_u)
        assert self.ma.has_add_permission(req)

    def test_doctor_can_add(self):
        req = _make_request(self.factory, self.doctor_u)
        assert self.ma.has_add_permission(req)

    def test_nurse_cannot_add(self):
        req = _make_request(self.factory, self.nurse_u)
        assert not self.ma.has_add_permission(req)

    def test_pharmacy_cannot_add(self):
        req = _make_request(self.factory, self.pharm_u)
        assert not self.ma.has_add_permission(req)

    def test_patient_cannot_add(self):
        req = _make_request(self.factory, self.patient_u)
        assert not self.ma.has_add_permission(req)

    # change_permission
    def test_admin_can_change(self):
        req = _make_request(self.factory, self.admin_u)
        assert self.ma.has_change_permission(req)
        assert self.ma.has_change_permission(req, self.med_obj)

    def test_doctor_can_change_assigned_patient_med(self):
        req = _make_request(self.factory, self.doctor_u)
        assert self.ma.has_change_permission(req, self.med_obj)

    def test_doctor_cannot_change_unassigned_med(self):
        req = _make_request(self.factory, self.doctor_u)
        assert not self.ma.has_change_permission(req, self.med_other)

    def test_nurse_cannot_change(self):
        req = _make_request(self.factory, self.nurse_u)
        assert not self.ma.has_change_permission(req)

    def test_pharmacy_cannot_change(self):
        req = _make_request(self.factory, self.pharm_u)
        assert not self.ma.has_change_permission(req)

    # delete_permission
    def test_superuser_can_delete(self):
        req = _make_request(self.factory, self.superuser)
        assert self.ma.has_delete_permission(req)

    def test_admin_can_delete(self):
        req = _make_request(self.factory, self.admin_u)
        assert self.ma.has_delete_permission(req)

    def test_doctor_cannot_delete(self):
        req = _make_request(self.factory, self.doctor_u)
        assert not self.ma.has_delete_permission(req)

    def test_nurse_cannot_delete(self):
        req = _make_request(self.factory, self.nurse_u)
        assert not self.ma.has_delete_permission(req)

    # view_permission
    def test_admin_can_view(self):
        req = _make_request(self.factory, self.admin_u)
        assert self.ma.has_view_permission(req)

    def test_doctor_can_view(self):
        req = _make_request(self.factory, self.doctor_u)
        assert self.ma.has_view_permission(req)

    def test_nurse_can_view(self):
        req = _make_request(self.factory, self.nurse_u)
        assert self.ma.has_view_permission(req)

    def test_pharmacy_can_view(self):
        req = _make_request(self.factory, self.pharm_u)
        assert self.ma.has_view_permission(req)

    def test_patient_cannot_view_standalone_admin(self):
        req = _make_request(self.factory, self.patient_u)
        assert not self.ma.has_view_permission(req)

    # module_permission (sidebar visibility)
    def test_patient_module_hidden(self):
        req = _make_request(self.factory, self.patient_u)
        assert not self.ma.has_module_permission(req)

    def test_nurse_module_visible(self):
        req = _make_request(self.factory, self.nurse_u)
        assert self.ma.has_module_permission(req)


# ─────────────────────────────────────────────────────────────────────────────
# 7. PatientAdmin — Medical History fieldset visibility
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.admin
class TestPatientAdminMedicalHistoryFieldsets:
    """PatientAdmin.get_fieldsets() exposes/hides Medical History per role."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.factory = RequestFactory()

        self.doc = _make_doctor_user("doc_fs")
        self.pat_user = _make_patient_user("pat_fs")
        patient = self.pat_user.profile.patient_record
        patient.assigned_doctor = self.doc.profile
        patient.save()
        self.patient_obj = patient

        def _staff(username, role, lic="X-FS"):
            u = User.objects.create_user(
                username, password="pass", is_staff=True
            )
            UserProfile.objects.create(user=u, role=role, license_number=lic)
            return u

        self.admin_u = _staff("admin_fs", "admin", "A-FS")
        self.nurse_u = _staff("nurse_fs", "nurse", "N-FS")
        self.pharm_u = _staff("pharm_fs", "pharmacy", "P-FS")
        self.su = User.objects.create_user(
            "su_fs", password="pass",
            is_staff=True, is_superuser=True
        )

    def _all_fieldnames(self, fieldsets):
        names = []
        for _title, opts in fieldsets:
            names.extend(opts.get("fields", ()))
        return names

    def test_admin_sees_medical_history_fields(self):
        req = _make_request(self.factory, self.admin_u)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f in names, f"admin missing {f}"

    def test_superuser_sees_medical_history_fields(self):
        req = _make_request(self.factory, self.su)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f in names

    def test_doctor_sees_medical_history_fields(self):
        req = _make_request(self.factory, self.doc)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f in names, f"doctor missing {f}"

    def test_nurse_sees_medical_history_fields(self):
        req = _make_request(self.factory, self.nurse_u)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f in names, f"nurse missing {f}"

    def test_patient_hides_medical_history_fields(self):
        """Patients must not see their own diagnoses/procedures in admin."""
        req = _make_request(self.factory, self.pat_user)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        for f in ("diagnoses", "procedures", "visit_notes", "chronic_conditions"):
            assert f not in names, f"patient should not see {f}"

    def test_pharmacy_sees_allergies_not_diagnoses(self):
        """Pharmacy sees Allergy Information but not diagnoses/procedures."""
        req = _make_request(self.factory, self.pharm_u)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        names = self._all_fieldnames(fs)
        assert "allergies" in names
        assert "diagnoses" not in names
        assert "procedures" not in names

    def test_medical_history_section_title_in_doctor_fieldsets(self):
        req = _make_request(self.factory, self.doc)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        titles = [t for t, _ in fs]
        assert "Medical History" in titles

    def test_medical_history_section_title_in_nurse_fieldsets(self):
        req = _make_request(self.factory, self.nurse_u)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        titles = [t for t, _ in fs]
        assert "Medical History" in titles

    def test_pharmacy_allergy_section_title(self):
        req = _make_request(self.factory, self.pharm_u)
        fs = self.pa.get_fieldsets(req, self.patient_obj)
        titles = [t for t, _ in fs]
        assert "Allergy Information" in titles


# ─────────────────────────────────────────────────────────────────────────────
# 8. PatientAdmin — Medical History readonly enforcement (FR-D-4 / FR-N-2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.admin
class TestPatientAdminMedicalHistoryReadonly:
    """Medical-history fields are readonly for nurse/pharmacy, editable for doctor."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.factory = RequestFactory()

        self.pat_user = _make_patient_user("pat_ro")
        self.patient_obj = self.pat_user.profile.patient_record

        def _staff(username, role, lic="X-RO"):
            u = User.objects.create_user(
                username, password="pass", is_staff=True
            )
            UserProfile.objects.create(user=u, role=role, license_number=lic)
            return u

        self.doctor_u = _staff("doc_ro", "doctor", "D-RO")
        self.nurse_u = _staff("nurse_ro", "nurse", "N-RO")
        self.pharm_u = _staff("pharm_ro", "pharmacy", "P-RO")
        self.admin_u = _staff("admin_ro", "admin", "A-RO")

    def test_nurse_has_all_history_fields_readonly(self):
        req = _make_request(self.factory, self.nurse_u)
        ro = self.pa.get_readonly_fields(req, self.patient_obj)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f in ro, f"nurse: {f} should be readonly"

    def test_pharmacy_has_allergies_readonly(self):
        req = _make_request(self.factory, self.pharm_u)
        ro = self.pa.get_readonly_fields(req, self.patient_obj)
        assert "allergies" in ro

    def test_doctor_does_not_have_history_fields_in_readonly(self):
        """Doctors should be able to EDIT medical history fields."""
        req = _make_request(self.factory, self.doctor_u)
        ro = self.pa.get_readonly_fields(req, self.patient_obj)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f not in ro, f"doctor should NOT have {f} readonly"

    def test_admin_does_not_have_history_fields_in_readonly(self):
        req = _make_request(self.factory, self.admin_u)
        ro = self.pa.get_readonly_fields(req, self.patient_obj)
        for f in ("diagnoses", "procedures", "visit_notes",
                  "allergies", "chronic_conditions"):
            assert f not in ro


# ─────────────────────────────────────────────────────────────────────────────
# 9. PatientAdmin — get_inlines() per role
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.admin
class TestPatientAdminInlines:
    """MedicationInline shown for clinical staff, hidden for patient role."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        from core.admin import EmergencyContactInline, MedicationInline

        self.EmergencyContactInline = EmergencyContactInline
        self.MedicationInline = MedicationInline

        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.factory = RequestFactory()

        self.pat_user = _make_patient_user("pat_inl")
        self.patient_obj = self.pat_user.profile.patient_record

        def _staff(username, role, lic="X-IL"):
            u = User.objects.create_user(
                username, password="pass", is_staff=True
            )
            UserProfile.objects.create(user=u, role=role, license_number=lic)
            return u

        self.admin_u = _staff("admin_inl", "admin", "A-IL")
        self.doctor_u = _staff("doc_inl", "doctor", "D-IL")
        self.nurse_u = _staff("nurse_inl", "nurse", "N-IL")
        self.pharm_u = _staff("pharm_inl", "pharmacy", "P-IL")
        self.su = User.objects.create_user(
            "su_inl", password="pass",
            is_staff=True, is_superuser=True
        )

    def test_admin_gets_medication_inline(self):
        req = _make_request(self.factory, self.admin_u)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline in inlines

    def test_doctor_gets_medication_inline(self):
        req = _make_request(self.factory, self.doctor_u)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline in inlines

    def test_nurse_gets_medication_inline(self):
        req = _make_request(self.factory, self.nurse_u)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline in inlines

    def test_pharmacy_gets_medication_inline(self):
        req = _make_request(self.factory, self.pharm_u)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline in inlines

    def test_patient_does_not_get_medication_inline(self):
        req = _make_request(self.factory, self.pat_user)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline not in inlines

    def test_superuser_gets_medication_inline(self):
        req = _make_request(self.factory, self.su)
        inlines = self.pa.get_inlines(req, self.patient_obj)
        assert self.MedicationInline in inlines

    def test_all_roles_include_emergency_contact_inline(self):
        for user in (
            self.admin_u, self.doctor_u, self.nurse_u,
            self.pharm_u, self.pat_user, self.su
        ):
            req = _make_request(self.factory, user)
            inlines = self.pa.get_inlines(req, self.patient_obj)
            assert self.EmergencyContactInline in inlines


# ─────────────────────────────────────────────────────────────────────────────
# 10. HTTP tests — MedicationAdmin changelist and PatientAdmin
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
class TestMedicationAdminHTTP:
    """HTTP-level smoke tests for MedicationAdmin changelist."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.client = Client()

        # Superuser
        self.admin_user = User.objects.create_user(
            "http_su_med", password="pass",
            is_staff=True, is_superuser=True
        )

        # Doctor with assigned patient
        self.doc = _make_doctor_user("http_doc_med")
        self.pat_user = _make_patient_user("http_pat_med")
        patient = self.pat_user.profile.patient_record
        patient.assigned_doctor = self.doc.profile
        patient.save()
        self.patient = patient

        # Medications
        self.med_current = _make_med(
            patient, doctor=self.doc, name="Metformin", status="current"
        )
        self.med_past = _make_med(
            patient, doctor=self.doc, name="Penicillin", status="past",
            end_date=YESTERDAY
        )

        # Nurse
        self.nurse = User.objects.create_user(
            "http_nurse_med", password="pass", is_staff=True
        )
        UserProfile.objects.create(
            user=self.nurse, role="nurse", license_number="RN-HTTP"
        )

    def test_superuser_changelist_loads_200(self):
        self.client.force_login(self.admin_user)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200

    def test_doctor_changelist_loads_200(self):
        self.client.force_login(self.doc)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200

    def test_nurse_changelist_loads_200(self):
        self.client.force_login(self.nurse)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200

    def test_superuser_changelist_shows_medications(self):
        self.client.force_login(self.admin_user)
        resp = self.client.get("/admin/core/medication/")
        content = resp.content.decode()
        assert "Metformin" in content

    def test_doctor_sees_assigned_medication(self):
        self.client.force_login(self.doc)
        resp = self.client.get("/admin/core/medication/")
        content = resp.content.decode()
        assert "Metformin" in content

    def test_filter_by_status_current(self):
        self.client.force_login(self.admin_user)
        resp = self.client.get("/admin/core/medication/?status=current")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Metformin" in content

    def test_filter_by_status_past(self):
        self.client.force_login(self.admin_user)
        resp = self.client.get("/admin/core/medication/?status=past")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Penicillin" in content

    def test_patient_user_cannot_access_medication_admin(self):
        """Patient role — medication admin module is hidden (403/302)."""
        self.client.force_login(self.pat_user)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code in (302, 403)


@pytest.mark.django_db
@pytest.mark.integration
class TestPatientAdminMedicalHistoryHTTP:
    """HTTP smoke test: PatientAdmin change page includes Medical History."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.client = Client()
        self.su = User.objects.create_user(
            "http_su_mhist", password="pass",
            is_staff=True, is_superuser=True
        )
        pat_user = _make_patient_user("http_ph_pat")
        self.patient = pat_user.profile.patient_record

    def test_patient_change_page_includes_medical_history_section(self):
        self.client.force_login(self.su)
        resp = self.client.get(
            f"/admin/core/patient/{self.patient.pk}/change/"
        )
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Medical History" in content

    def test_patient_change_page_includes_diagnoses_field(self):
        self.client.force_login(self.su)
        resp = self.client.get(
            f"/admin/core/patient/{self.patient.pk}/change/"
        )
        content = resp.content.decode()
        assert "diagnoses" in content

    def test_doctor_change_page_includes_medical_history(self):
        doc = _make_doctor_user("http_doc_mhist")
        self.patient.assigned_doctor = doc.profile
        self.patient.save()
        self.client.force_login(doc)
        resp = self.client.get(
            f"/admin/core/patient/{self.patient.pk}/change/"
        )
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Medical History" in content

    def test_nurse_change_page_includes_medical_history(self):
        nurse = User.objects.create_user(
            "http_nurse_mhist", password="pass", is_staff=True
        )
        UserProfile.objects.create(
            user=nurse, role="nurse", license_number="RN-HTTP2"
        )
        self.client.force_login(nurse)
        resp = self.client.get(
            f"/admin/core/patient/{self.patient.pk}/change/"
        )
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Medical History" in content
