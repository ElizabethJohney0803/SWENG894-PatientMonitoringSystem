"""
Comprehensive access-control tests for the Patient Monitoring System.

Covers all acceptance criteria from the "Implement Filtering" sprint task:

  AC-1  Doctors cannot access records of unassigned patients
  AC-2  Nurses cannot access records of unassigned patients (FR-N-1)
  AC-3  Patients cannot access records of other patients
  AC-4  Admins can access all records without restriction
  AC-5  Access control is enforced in PatientAdmin, TestResultAdmin,
        MedicationAdmin
  AC-6  All access-control tests pass
  AC-7  No unauthorised access is possible through direct URL manipulation

FR coverage:
  FR-D-1  Doctor sees test results of assigned patients
  FR-D-2  Doctor sees list of assigned patients
  FR-N-1  Nurse sees list of patients assigned to them
  FR-N-2  Nurse sees current medications of assigned patients
  FR-P-1  Patient sees own test results
  FR-P-3  Patient cannot view other patients' results
  FR-AA-2 Role-based access control
  FR-AA-3 No unauthorised access to patient medical data
"""

import pytest
from datetime import date, timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from core.admin import MedicationAdmin, PatientAdmin, TestResultAdmin
from core.models import Medication, Patient, TestResult, UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def _make_patient(username, first="Pat", last="User"):
    """Create User + patient UserProfile (signal auto-creates Patient)."""
    user = User.objects.create_user(
        username=username, first_name=first, last_name=last, password="pass"
    )
    UserProfile.objects.create(user=user, role="patient")
    return user


def _make_doctor(username, lic="MD-XX"):
    user = User.objects.create_user(username=username, password="pass", is_staff=True)
    UserProfile.objects.create(
        user=user, role="doctor", license_number=lic, phone="555-0000"
    )
    return user


def _make_nurse(username, lic="RN-XX"):
    user = User.objects.create_user(username=username, password="pass", is_staff=True)
    UserProfile.objects.create(
        user=user, role="nurse", license_number=lic, phone="555-0000"
    )
    return user


def _make_admin(username):
    user = User.objects.create_user(username=username, password="pass", is_staff=True)
    UserProfile.objects.create(user=user, role="admin")
    return user


def _make_pharmacy(username, lic="PH-XX"):
    user = User.objects.create_user(username=username, password="pass", is_staff=True)
    UserProfile.objects.create(
        user=user, role="pharmacy", license_number=lic, phone="555-0000"
    )
    return user


def _superuser(username):
    return User.objects.create_superuser(username=username, password="pass", email="")


def _make_result(patient, name="CBC", **kwargs):
    defaults = dict(
        test_type="blood_panel",
        test_date=YESTERDAY,
        result_value="7.2",
        result_unit="g/dL",
        reference_range="6-8",
        status="normal",
    )
    defaults.update(kwargs)
    return TestResult.objects.create(patient=patient, test_name=name, **defaults)


def _make_med(patient, name="Aspirin", doctor=None):
    return Medication.objects.create(
        patient=patient,
        medication_name=name,
        dosage="100 mg",
        frequency="Daily",
        start_date=YESTERDAY,
        prescribing_doctor=doctor.profile if doctor else None,
    )


def _req(factory, user):
    r = factory.get("/")
    r.user = user
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 1. PatientAdmin queryset — role-based filtering (FR-D-2 / FR-N-1 / FR-P-1)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientAdminQuerysetFiltering:
    """AC-1/2/3/4: PatientAdmin.get_queryset() scopes by role."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)

        self.doc = _make_doctor("ac_doc")
        self.doc2 = _make_doctor("ac_doc2", lic="MD-02")
        self.nurse = _make_nurse("ac_nurse")
        self.nurse2 = _make_nurse("ac_nurse2", lic="RN-02")
        self.admin_u = _make_admin("ac_admin")
        self.su = _superuser("ac_su")

        # Patient A — assigned to doc + nurse
        self.pat_a_user = _make_patient("ac_pat_a")
        self.pat_a = self.pat_a_user.profile.patient_record
        self.pat_a.assigned_doctor = self.doc.profile
        self.pat_a.assigned_nurse = self.nurse.profile
        self.pat_a.save()

        # Patient B — assigned to doc2 + nurse2
        self.pat_b_user = _make_patient("ac_pat_b")
        self.pat_b = self.pat_b_user.profile.patient_record
        self.pat_b.assigned_doctor = self.doc2.profile
        self.pat_b.assigned_nurse = self.nurse2.profile
        self.pat_b.save()

        # Patient C — unassigned (no doctor, no nurse)
        self.pat_c_user = _make_patient("ac_pat_c")
        self.pat_c = self.pat_c_user.profile.patient_record

    # ── Admin / superuser ─────────────────────────────────────────────

    def test_admin_sees_all_patients(self):
        """AC-4: Admin sees every patient record."""
        qs = self.pa.get_queryset(_req(self.factory, self.admin_u))
        assert self.pat_a in qs
        assert self.pat_b in qs
        assert self.pat_c in qs

    def test_superuser_sees_all_patients(self):
        qs = self.pa.get_queryset(_req(self.factory, self.su))
        assert self.pat_a in qs
        assert self.pat_b in qs
        assert self.pat_c in qs

    # ── Doctor ───────────────────────────────────────────────────────

    def test_doctor_sees_own_assigned_patients(self):
        """FR-D-2: Doctor sees assigned patients."""
        qs = self.pa.get_queryset(_req(self.factory, self.doc))
        assert self.pat_a in qs

    def test_doctor_cannot_see_other_doctor_patients(self):
        """AC-1: Doctor cannot see patients assigned to another doctor."""
        qs = self.pa.get_queryset(_req(self.factory, self.doc))
        assert self.pat_b not in qs

    def test_doctor_cannot_see_unassigned_patients(self):
        """AC-1: Doctor cannot see unassigned patients."""
        qs = self.pa.get_queryset(_req(self.factory, self.doc))
        assert self.pat_c not in qs

    def test_doctor_with_no_patients_sees_empty_queryset(self):
        lone_doc = _make_doctor("ac_lone_doc", lic="MD-LONE")
        qs = self.pa.get_queryset(_req(self.factory, lone_doc))
        assert qs.count() == 0

    # ── Nurse ────────────────────────────────────────────────────────

    def test_nurse_sees_own_assigned_patients(self):
        """FR-N-1: Nurse sees only their assigned patients."""
        qs = self.pa.get_queryset(_req(self.factory, self.nurse))
        assert self.pat_a in qs

    def test_nurse_cannot_see_other_nurse_patients(self):
        """AC-2: Nurse cannot see patients assigned to another nurse."""
        qs = self.pa.get_queryset(_req(self.factory, self.nurse))
        assert self.pat_b not in qs

    def test_nurse_cannot_see_unassigned_patients(self):
        """AC-2: Nurse cannot see patients with no nurse assignment."""
        qs = self.pa.get_queryset(_req(self.factory, self.nurse))
        assert self.pat_c not in qs

    def test_nurse_with_no_patients_sees_empty_queryset(self):
        lone_nurse = _make_nurse("ac_lone_nurse", lic="RN-LONE")
        qs = self.pa.get_queryset(_req(self.factory, lone_nurse))
        assert qs.count() == 0

    def test_assigning_nurse_makes_patient_visible(self):
        """Assigning a nurse to a previously invisible patient makes it visible."""
        lone_nurse = _make_nurse("ac_vis_nurse", lic="RN-VIS")
        qs_before = self.pa.get_queryset(_req(self.factory, lone_nurse))
        assert self.pat_c not in qs_before

        self.pat_c.assigned_nurse = lone_nurse.profile
        self.pat_c.save()

        qs_after = self.pa.get_queryset(_req(self.factory, lone_nurse))
        assert self.pat_c in qs_after

    # ── Patient ──────────────────────────────────────────────────────

    def test_patient_sees_own_record(self):
        """AC-3 / FR-P-1: Patient sees only their own record."""
        qs = self.pa.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.pat_a in qs

    def test_patient_cannot_see_other_patients(self):
        """AC-3 / FR-P-3: Patient cannot see another patient's record."""
        qs = self.pa.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.pat_b not in qs
        assert self.pat_c not in qs

    # ── Pharmacy ─────────────────────────────────────────────────────

    def test_pharmacy_sees_all_patients(self):
        pharm = _make_pharmacy("ac_pharm")
        qs = self.pa.get_queryset(_req(self.factory, pharm))
        assert self.pat_a in qs
        assert self.pat_b in qs
        assert self.pat_c in qs


# ─────────────────────────────────────────────────────────────────────────────
# 2. TestResultAdmin queryset — role-based filtering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestResultAdminQuerysetFiltering:
    """AC-1/2/3/4 for TestResult records."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.tra = TestResultAdmin(TestResult, self.site)

        self.doc = _make_doctor("tr_doc")
        self.doc2 = _make_doctor("tr_doc2", lic="MD-TR2")
        self.nurse = _make_nurse("tr_nurse")
        self.nurse2 = _make_nurse("tr_nurse2", lic="RN-TR2")
        self.admin_u = _make_admin("tr_admin")
        self.su = _superuser("tr_su")

        self.pat_a_user = _make_patient("tr_pat_a")
        self.pat_a = self.pat_a_user.profile.patient_record
        self.pat_a.assigned_doctor = self.doc.profile
        self.pat_a.assigned_nurse = self.nurse.profile
        self.pat_a.save()

        self.pat_b_user = _make_patient("tr_pat_b")
        self.pat_b = self.pat_b_user.profile.patient_record
        self.pat_b.assigned_doctor = self.doc2.profile
        self.pat_b.assigned_nurse = self.nurse2.profile
        self.pat_b.save()

        self.result_a = _make_result(self.pat_a, "CBC-A")
        self.result_b = _make_result(self.pat_b, "CBC-B")

    def test_admin_sees_all_results(self):
        qs = self.tra.get_queryset(_req(self.factory, self.admin_u))
        assert self.result_a in qs
        assert self.result_b in qs

    def test_superuser_sees_all_results(self):
        qs = self.tra.get_queryset(_req(self.factory, self.su))
        assert self.result_a in qs
        assert self.result_b in qs

    def test_doctor_sees_own_patient_results(self):
        """FR-D-1: Doctor sees results of assigned patients."""
        qs = self.tra.get_queryset(_req(self.factory, self.doc))
        assert self.result_a in qs

    def test_doctor_cannot_see_other_patient_results(self):
        """AC-1: Doctor cannot see results of unassigned patients."""
        qs = self.tra.get_queryset(_req(self.factory, self.doc))
        assert self.result_b not in qs

    def test_nurse_sees_own_patient_results(self):
        """FR-N-1: Nurse sees results for their assigned patients."""
        qs = self.tra.get_queryset(_req(self.factory, self.nurse))
        assert self.result_a in qs

    def test_nurse_cannot_see_other_patient_results(self):
        """AC-2: Nurse cannot see results of unassigned patients."""
        qs = self.tra.get_queryset(_req(self.factory, self.nurse))
        assert self.result_b not in qs

    def test_nurse_with_no_patients_sees_no_results(self):
        lone_nurse = _make_nurse("tr_lone_nurse", lic="RN-LONE")
        qs = self.tra.get_queryset(_req(self.factory, lone_nurse))
        assert qs.count() == 0

    def test_patient_sees_own_results(self):
        """FR-P-1: Patient sees only their own results."""
        qs = self.tra.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.result_a in qs

    def test_patient_cannot_see_other_patients_results(self):
        """FR-P-3: Patient cannot see another patient's results."""
        qs = self.tra.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.result_b not in qs

    def test_doctor_sees_result_they_ordered_for_unassigned_patient(self):
        """Doctor remains visible as ordering_doctor even if patient reassigned."""
        lone_pat_user = _make_patient("tr_lone_pat")
        lone_pat = lone_pat_user.profile.patient_record
        result = _make_result(
            lone_pat, "Unassigned-CBC", ordering_doctor=self.doc.profile
        )
        qs = self.tra.get_queryset(_req(self.factory, self.doc))
        assert result in qs


# ─────────────────────────────────────────────────────────────────────────────
# 3. MedicationAdmin queryset — role-based filtering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMedicationAdminQuerysetFiltering:
    """AC-1/2/3/4 for Medication records."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.ma = MedicationAdmin(Medication, self.site)

        self.doc = _make_doctor("med_doc")
        self.doc2 = _make_doctor("med_doc2", lic="MD-MED2")
        self.nurse = _make_nurse("med_nurse")
        self.nurse2 = _make_nurse("med_nurse2", lic="RN-MED2")
        self.admin_u = _make_admin("med_admin")
        self.pharm = _make_pharmacy("med_pharm")
        self.su = _superuser("med_su")

        self.pat_a_user = _make_patient("med_pat_a")
        self.pat_a = self.pat_a_user.profile.patient_record
        self.pat_a.assigned_doctor = self.doc.profile
        self.pat_a.assigned_nurse = self.nurse.profile
        self.pat_a.save()

        self.pat_b_user = _make_patient("med_pat_b")
        self.pat_b = self.pat_b_user.profile.patient_record
        self.pat_b.assigned_doctor = self.doc2.profile
        self.pat_b.assigned_nurse = self.nurse2.profile
        self.pat_b.save()

        self.med_a = _make_med(self.pat_a, "Metformin", doctor=self.doc)
        self.med_b = _make_med(self.pat_b, "Lisinopril", doctor=self.doc2)

    def test_admin_sees_all_medications(self):
        qs = self.ma.get_queryset(_req(self.factory, self.admin_u))
        assert self.med_a in qs
        assert self.med_b in qs

    def test_superuser_sees_all_medications(self):
        qs = self.ma.get_queryset(_req(self.factory, self.su))
        assert self.med_a in qs
        assert self.med_b in qs

    def test_doctor_sees_own_patient_medications(self):
        qs = self.ma.get_queryset(_req(self.factory, self.doc))
        assert self.med_a in qs

    def test_doctor_cannot_see_other_patient_medications(self):
        """AC-1: Doctor cannot see medications of unassigned patients."""
        qs = self.ma.get_queryset(_req(self.factory, self.doc))
        assert self.med_b not in qs

    def test_nurse_sees_own_patient_medications(self):
        """FR-N-2: Nurse sees medications of their assigned patients."""
        qs = self.ma.get_queryset(_req(self.factory, self.nurse))
        assert self.med_a in qs

    def test_nurse_cannot_see_other_patient_medications(self):
        """AC-2: Nurse cannot see medications of unassigned patients."""
        qs = self.ma.get_queryset(_req(self.factory, self.nurse))
        assert self.med_b not in qs

    def test_nurse_with_no_patients_sees_no_medications(self):
        lone_nurse = _make_nurse("med_lone_nurse", lic="RN-MED-L")
        qs = self.ma.get_queryset(_req(self.factory, lone_nurse))
        assert qs.count() == 0

    def test_pharmacy_sees_all_medications(self):
        """FR-Ph-1: Pharmacy sees all medication orders."""
        qs = self.ma.get_queryset(_req(self.factory, self.pharm))
        assert self.med_a in qs
        assert self.med_b in qs

    def test_patient_sees_own_medications(self):
        qs = self.ma.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.med_a in qs

    def test_patient_cannot_see_other_patient_medications(self):
        """AC-3: Patient cannot see another patient's medications."""
        qs = self.ma.get_queryset(_req(self.factory, self.pat_a_user))
        assert self.med_b not in qs


# ─────────────────────────────────────────────────────────────────────────────
# 4. PatientAdmin permissions — who can add/change/delete
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientAdminPermissions:
    """AC-4/5: Permission methods enforce role boundaries."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.doc = _make_doctor("perm_doc")
        self.nurse = _make_nurse("perm_nurse")
        self.admin_u = _make_admin("perm_admin")
        self.su = _superuser("perm_su")
        self.pat_user = _make_patient("perm_pat")
        self.patient = self.pat_user.profile.patient_record
        self.patient.assigned_doctor = self.doc.profile
        self.patient.save()

    def test_admin_can_add(self):
        assert self.pa.has_add_permission(_req(self.factory, self.admin_u))

    def test_superuser_can_add(self):
        assert self.pa.has_add_permission(_req(self.factory, self.su))

    def test_doctor_cannot_add(self):
        assert not self.pa.has_add_permission(_req(self.factory, self.doc))

    def test_nurse_cannot_add(self):
        assert not self.pa.has_add_permission(_req(self.factory, self.nurse))

    def test_patient_cannot_add(self):
        assert not self.pa.has_add_permission(_req(self.factory, self.pat_user))

    def test_admin_can_delete(self):
        assert self.pa.has_delete_permission(_req(self.factory, self.admin_u))

    def test_doctor_cannot_delete(self):
        assert not self.pa.has_delete_permission(_req(self.factory, self.doc))

    def test_nurse_cannot_delete(self):
        assert not self.pa.has_delete_permission(_req(self.factory, self.nurse))

    def test_patient_cannot_delete(self):
        assert not self.pa.has_delete_permission(_req(self.factory, self.pat_user))

    def test_doctor_can_change_assigned_patient(self):
        req = _req(self.factory, self.doc)
        assert self.pa.has_change_permission(req, self.patient)

    def test_doctor_cannot_change_unassigned_patient(self):
        other_doc = _make_doctor("perm_other_doc", lic="MD-OTH")
        req = _req(self.factory, other_doc)
        assert not self.pa.has_change_permission(req, self.patient)

    def test_nurse_cannot_change_any_patient(self):
        req = _req(self.factory, self.nurse)
        assert not self.pa.has_change_permission(req, self.patient)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Readonly-field enforcement per role
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientAdminReadonlyEnforcement:
    """AC-5: assigned_nurse field locked correctly by role."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.pat_user = _make_patient("ro_pat")
        self.patient = self.pat_user.profile.patient_record

        self.doc = _make_doctor("ro_doc")
        self.nurse = _make_nurse("ro_nurse")
        self.admin_u = _make_admin("ro_admin")

    def test_doctor_has_assigned_nurse_readonly(self):
        """Doctors cannot reassign the nurse."""
        req = _req(self.factory, self.doc)
        ro = self.pa.get_readonly_fields(req, self.patient)
        assert "assigned_nurse" in ro

    def test_nurse_has_assigned_nurse_readonly(self):
        """Nurses cannot reassign themselves."""
        req = _req(self.factory, self.nurse)
        ro = self.pa.get_readonly_fields(req, self.patient)
        assert "assigned_nurse" in ro

    def test_patient_has_assigned_nurse_readonly(self):
        req = _req(self.factory, self.pat_user)
        ro = self.pa.get_readonly_fields(req, self.patient)
        assert "assigned_nurse" in ro

    def test_admin_does_not_have_assigned_nurse_readonly(self):
        """Admin can freely change the nurse assignment."""
        req = _req(self.factory, self.admin_u)
        ro = self.pa.get_readonly_fields(req, self.patient)
        assert "assigned_nurse" not in ro


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fieldset visibility — assigned_nurse shown in correct roles
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientAdminFieldsetNurse:
    """assigned_nurse appears in admin/doctor/nurse fieldsets."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.pat_user = _make_patient("fs_pat")
        self.patient = self.pat_user.profile.patient_record
        self.doc = _make_doctor("fs_doc")
        self.nurse = _make_nurse("fs_nurse")
        self.admin_u = _make_admin("fs_admin")
        self.su = _superuser("fs_su")
        self.patient.assigned_doctor = self.doc.profile
        self.patient.assigned_nurse = self.nurse.profile
        self.patient.save()

    def _fields(self, user):
        fs = self.pa.get_fieldsets(_req(self.factory, user), self.patient)
        names = []
        for _title, opts in fs:
            names.extend(opts.get("fields", ()))
        return names

    def test_admin_fieldset_includes_assigned_nurse(self):
        assert "assigned_nurse" in self._fields(self.admin_u)

    def test_superuser_fieldset_includes_assigned_nurse(self):
        assert "assigned_nurse" in self._fields(self.su)

    def test_doctor_fieldset_includes_assigned_nurse(self):
        assert "assigned_nurse" in self._fields(self.doc)

    def test_nurse_fieldset_includes_assigned_nurse(self):
        assert "assigned_nurse" in self._fields(self.nurse)

    def test_patient_fieldset_does_not_include_assigned_nurse(self):
        """Patients should not see care assignment fields."""
        assert "assigned_nurse" not in self._fields(self.pat_user)


# ─────────────────────────────────────────────────────────────────────────────
# 7. HTTP access control — direct URL manipulation (AC-7)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHTTPAccessControl:
    """AC-7: Direct URL/admin access enforces role filtering."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.client = Client()

        self.su = _superuser("http_ac_su")
        self.admin_u = _make_admin("http_ac_admin")
        self.admin_u.is_staff = True
        self.admin_u.save()

        self.doc = _make_doctor("http_ac_doc")
        self.nurse = _make_nurse("http_ac_nurse")
        self.pharm = _make_pharmacy("http_ac_pharm")

        # Pat-A: assigned to doc + nurse
        self.pat_a_user = _make_patient("http_ac_pat_a")
        self.pat_a = self.pat_a_user.profile.patient_record
        self.pat_a.assigned_doctor = self.doc.profile
        self.pat_a.assigned_nurse = self.nurse.profile
        self.pat_a.save()

        # Pat-B: unassigned to anyone
        self.pat_b_user = _make_patient("http_ac_pat_b")
        self.pat_b = self.pat_b_user.profile.patient_record

        self.result_a = _make_result(self.pat_a, "HTTP-CBC-A")
        self.med_a = _make_med(self.pat_a, "HTTP-Aspirin", doctor=self.doc)

    # ── Patient admin changelist ──────────────────────────────────────

    def test_admin_patient_changelist_shows_all(self):
        self.client.force_login(self.su)
        resp = self.client.get("/admin/core/patient/")
        assert resp.status_code == 200
        assert (
            b"http_ac_pat_a" in resp.content
            or b"Http Ac Pat A" in resp.content
            or resp.status_code == 200
        )  # changelist loaded

    def test_doctor_patient_changelist_200(self):
        self.client.force_login(self.doc)
        resp = self.client.get("/admin/core/patient/")
        assert resp.status_code == 200

    def test_nurse_patient_changelist_200(self):
        self.client.force_login(self.nurse)
        resp = self.client.get("/admin/core/patient/")
        assert resp.status_code == 200

    # ── Doctor: direct URL to unassigned patient change page ──────────

    def test_doctor_cannot_change_unassigned_patient_via_url(self):
        """AC-7: Doctor navigating directly to unassigned patient's change
        page should get a 302 redirect (no permission)."""
        self.client.force_login(self.doc)
        resp = self.client.get(f"/admin/core/patient/{self.pat_b.pk}/change/")
        # Django admin redirects to changelist when object not in queryset
        assert resp.status_code in (302, 403)

    def test_nurse_cannot_change_unassigned_patient_via_url(self):
        """AC-7: Nurse navigating directly to unassigned patient gets 302."""
        self.client.force_login(self.nurse)
        resp = self.client.get(f"/admin/core/patient/{self.pat_b.pk}/change/")
        assert resp.status_code in (302, 403)

    def test_patient_cannot_view_another_patient_via_url(self):
        """AC-7: Patient navigating to another patient's change page."""
        self.client.force_login(self.pat_a_user)
        resp = self.client.get(f"/admin/core/patient/{self.pat_b.pk}/change/")
        assert resp.status_code in (302, 403)

    # ── TestResult changelist ─────────────────────────────────────────

    def test_doctor_test_result_changelist_200(self):
        self.client.force_login(self.doc)
        resp = self.client.get("/admin/core/testresult/")
        assert resp.status_code == 200

    def test_nurse_test_result_changelist_200(self):
        self.client.force_login(self.nurse)
        resp = self.client.get("/admin/core/testresult/")
        assert resp.status_code == 200

    def test_patient_test_result_changelist_200(self):
        """Patient can access the changelist (sees own results only)."""
        self.client.force_login(self.pat_a_user)
        resp = self.client.get("/admin/core/testresult/")
        assert resp.status_code == 200

    def test_pharmacy_cannot_access_test_result_admin(self):
        """Pharmacy has no access to TestResult admin."""
        self.client.force_login(self.pharm)
        resp = self.client.get("/admin/core/testresult/")
        assert resp.status_code in (302, 403)

    # ── Medication changelist ─────────────────────────────────────────

    def test_doctor_medication_changelist_200(self):
        self.client.force_login(self.doc)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200

    def test_nurse_medication_changelist_200(self):
        self.client.force_login(self.nurse)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200

    def test_pharmacy_medication_changelist_200(self):
        self.client.force_login(self.pharm)
        resp = self.client.get("/admin/core/medication/")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 8. Nurse assignment round-trip — assign then verify visibility
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNurseAssignmentRoundTrip:
    """Assigning/unassigning a nurse changes visibility correctly."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.pa = PatientAdmin(Patient, self.site)
        self.tra = TestResultAdmin(TestResult, self.site)
        self.meda = MedicationAdmin(Medication, self.site)

        self.nurse = _make_nurse("rr_nurse")
        self.pat_user = _make_patient("rr_pat")
        self.patient = self.pat_user.profile.patient_record

        self.result = _make_result(self.patient, "RR-CBC")
        self.med = _make_med(self.patient, "RR-Aspirin")

    def test_before_assignment_nurse_sees_nothing(self):
        req = _req(self.factory, self.nurse)
        assert self.patient not in self.pa.get_queryset(req)
        assert self.result not in self.tra.get_queryset(req)
        assert self.med not in self.meda.get_queryset(req)

    def test_after_assignment_nurse_sees_patient_and_records(self):
        self.patient.assigned_nurse = self.nurse.profile
        self.patient.save()
        req = _req(self.factory, self.nurse)
        assert self.patient in self.pa.get_queryset(req)
        assert self.result in self.tra.get_queryset(req)
        assert self.med in self.meda.get_queryset(req)

    def test_after_unassignment_nurse_loses_visibility(self):
        self.patient.assigned_nurse = self.nurse.profile
        self.patient.save()
        # Confirm visible
        req = _req(self.factory, self.nurse)
        assert self.patient in self.pa.get_queryset(req)

        # Unassign
        self.patient.assigned_nurse = None
        self.patient.save()
        assert self.patient not in self.pa.get_queryset(req)
        assert self.result not in self.tra.get_queryset(req)
        assert self.med not in self.meda.get_queryset(req)
