"""
Tests for the TestResult model, admin queryset, permissions,
and HTTP changelist behaviour.

FR coverage:
  FR-P-1  Patient can view their own test results
  FR-P-2  Display: name, value, reference range, date
  FR-P-3  Patients cannot view other patients' results
  FR-D-1  Doctor can view test results of assigned patients
  FR-D-3  Results displayed chronologically per patient
  FR-AA-2 Role-based access
  FR-AA-3 No unauthorised access
"""

import pytest
from datetime import date, timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory

from core.admin import TestResultAdmin
from core.models import Patient, TestResult, UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TWO_DAYS_AGO = TODAY - timedelta(days=2)


def _make_patient_user(username, first="Pat", last="User"):
    """Create a User + patient UserProfile (auto-creates Patient record)."""
    user = User.objects.create_user(
        username=username,
        first_name=first,
        last_name=last,
        password="testpass",
    )
    UserProfile.objects.create(user=user, role="patient")
    return user


def _make_result(patient, test_name, test_date=None, **kwargs):
    """Create and return a TestResult for *patient*."""
    defaults = dict(
        test_type="blood_panel",
        test_date=test_date or YESTERDAY,
        result_value="7.2",
        result_unit="g/dL",
        reference_range="6.0-8.0 g/dL",
        status="normal",
    )
    defaults.update(kwargs)
    return TestResult.objects.create(
        patient=patient,
        test_name=test_name,
        **defaults,
    )


def _make_request(factory, user):
    req = factory.get("/")
    req.user = user
    return req


# ─────────────────────────────────────────────────────────────────────────────
# 1. Model field tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestTestResultModelFields:
    """Unit tests for TestResult model fields, defaults, and validation."""

    def test_create_with_required_fields(self, patient_user):
        """TestResult can be created with required fields only."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert tr.pk is not None
        assert tr.test_name == "CBC"

    def test_create_stores_all_fields(self, patient_user, doctor_user):
        """TestResult stores all optional fields correctly."""
        patient = patient_user.profile.patient_record
        tr = TestResult.objects.create(
            patient=patient,
            ordering_doctor=doctor_user.profile,
            test_name="Complete Blood Count",
            test_type="blood_panel",
            test_date=YESTERDAY,
            result_value="14.5",
            result_unit="g/dL",
            reference_range="12.0-17.5 g/dL",
            status="normal",
            doctor_notes="Within normal limits.",
            follow_up_required=False,
        )
        tr.refresh_from_db()
        assert tr.ordering_doctor == doctor_user.profile
        assert tr.result_unit == "g/dL"
        assert tr.reference_range == "12.0-17.5 g/dL"
        assert tr.status == "normal"
        assert tr.doctor_notes == "Within normal limits."
        assert tr.follow_up_required is False

    def test_default_status_is_pending(self, patient_user):
        """Default status should be 'pending'."""
        patient = patient_user.profile.patient_record
        tr = TestResult.objects.create(
            patient=patient,
            test_name="Lipid Panel",
            test_type="lipid_panel",
            test_date=YESTERDAY,
            result_value="Pending",
        )
        assert tr.status == "pending"

    def test_default_follow_up_is_false(self, patient_user):
        """follow_up_required defaults to False."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "Urinalysis")
        assert tr.follow_up_required is False

    def test_ordering_doctor_nullable(self, patient_user):
        """ordering_doctor can be None."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "Urinalysis", ordering_doctor=None)
        assert tr.ordering_doctor is None

    def test_str_representation(self, patient_user):
        """__str__ includes test name, patient full name, and date."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC", test_date=YESTERDAY)
        s = str(tr)
        assert "CBC" in s
        assert str(YESTERDAY) in s
        assert "Bob Johnson" in s  # patient_user fixture names

    def test_future_test_date_raises_validation_error(self, patient_user):
        """Test date cannot be in the future."""
        patient = patient_user.profile.patient_record
        tr = TestResult(
            patient=patient,
            test_name="Future Test",
            test_type="other",
            test_date=TODAY + timedelta(days=1),
            result_value="TBD",
            status="pending",
        )
        with pytest.raises(ValidationError) as exc_info:
            tr.clean()
        assert "test_date" in str(exc_info.value)

    def test_today_test_date_is_valid(self, patient_user):
        """Test date equal to today should pass validation."""
        patient = patient_user.profile.patient_record
        tr = TestResult(
            patient=patient,
            test_name="Today Test",
            test_type="other",
            test_date=TODAY,
            result_value="Normal",
            status="normal",
        )
        tr.clean()  # should not raise

    def test_non_doctor_ordering_doctor_raises_validation(
        self, patient_user, nurse_user
    ):
        """ordering_doctor must have role='doctor'."""
        patient = patient_user.profile.patient_record
        tr = TestResult(
            patient=patient,
            ordering_doctor=nurse_user.profile,
            test_name="CBC",
            test_type="blood_panel",
            test_date=YESTERDAY,
            result_value="7.2",
            status="normal",
        )
        with pytest.raises(ValidationError) as exc_info:
            tr.clean()
        assert "ordering_doctor" in str(exc_info.value)

    def test_all_test_type_choices_save(self, patient_user):
        """All TEST_TYPE_CHOICES values can be saved."""
        patient = patient_user.profile.patient_record
        for code, _ in TestResult.TEST_TYPE_CHOICES:
            tr = TestResult.objects.create(
                patient=patient,
                test_name=f"Test {code}",
                test_type=code,
                test_date=YESTERDAY,
                result_value="OK",
                status="normal",
            )
            assert tr.test_type == code

    def test_all_status_choices_save(self, patient_user):
        """All STATUS_CHOICES values can be saved."""
        patient = patient_user.profile.patient_record
        for code, _ in TestResult.STATUS_CHOICES:
            tr = TestResult.objects.create(
                patient=patient,
                test_name=f"Status {code}",
                test_type="other",
                test_date=YESTERDAY,
                result_value="v",
                status=code,
            )
            assert tr.status == code

    def test_timestamps_auto_set_on_creation(self, patient_user):
        """created_at and updated_at are auto-populated."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "Hormone Panel")
        assert tr.created_at is not None
        assert tr.updated_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Relationship tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestTestResultRelationships:
    """Tests for FK relationships and reverse managers."""

    def test_patient_test_results_reverse_manager(self, patient_user):
        """Patient.test_results reverse manager works."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "CBC")
        _make_result(patient, "Urinalysis")
        assert patient.test_results.count() == 2

    def test_doctor_ordered_tests_reverse_manager(self, patient_user, doctor_user):
        """UserProfile.ordered_tests reverse manager works."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "CBC", ordering_doctor=doctor_user.profile)
        assert doctor_user.profile.ordered_tests.count() == 1

    def test_cascade_delete_with_patient(self, patient_user):
        """Deleting a Patient cascades to its TestResults."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        tr_pk = tr.pk
        patient.delete()
        assert not TestResult.objects.filter(pk=tr_pk).exists()

    def test_delete_doctor_sets_ordering_doctor_null(self, patient_user, doctor_user):
        """Deleting a doctor's User sets ordering_doctor to NULL."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC", ordering_doctor=doctor_user.profile)
        doctor_user.delete()
        tr.refresh_from_db()
        assert tr.ordering_doctor is None

    def test_multiple_results_per_patient(self, patient_user):
        """A patient can have multiple test results."""
        patient = patient_user.profile.patient_record
        for i in range(5):
            _make_result(patient, f"Test {i}")
        assert patient.test_results.count() == 5


# ─────────────────────────────────────────────────────────────────────────────
# 3. Chronological ordering (FR-D-3)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.models
class TestTestResultOrdering:
    """FR-D-3: results must be ordered chronologically, newest first."""

    def test_queryset_ordered_newest_first(self, patient_user):
        """Default Meta ordering returns most recent test first."""
        patient = patient_user.profile.patient_record
        older = _make_result(patient, "CBC", test_date=TWO_DAYS_AGO)
        newer = _make_result(patient, "Lipid Panel", test_date=YESTERDAY)

        results = list(TestResult.objects.filter(patient=patient))
        assert results[0].pk == newer.pk
        assert results[1].pk == older.pk

    def test_patient_manager_ordered_newest_first(self, patient_user):
        """patient.test_results follows the chronological ordering."""
        patient = patient_user.profile.patient_record
        older = _make_result(patient, "CBC", test_date=TWO_DAYS_AGO)
        newer = _make_result(patient, "Lipid Panel", test_date=YESTERDAY)

        results = list(patient.test_results.all())
        assert results[0].pk == newer.pk
        assert results[1].pk == older.pk


# ─────────────────────────────────────────────────────────────────────────────
# 4. Admin queryset (role scoping)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestTestResultAdminQueryset:
    """get_queryset() returns role-scoped results."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.tra = TestResultAdmin(TestResult, self.site)

    def test_admin_sees_all_results(self, admin_user, patient_user):
        patient = patient_user.profile.patient_record
        _make_result(patient, "CBC")
        qs = self.tra.get_queryset(_make_request(self.factory, admin_user))
        assert qs.count() >= 1

    def test_superuser_sees_all_results(self, django_user_model, patient_user):
        su = django_user_model.objects.create_superuser(
            username="su_tr", password="pass"
        )
        patient = patient_user.profile.patient_record
        _make_result(patient, "CBC")
        qs = self.tra.get_queryset(_make_request(self.factory, su))
        assert qs.count() >= 1

    def test_doctor_sees_assigned_patient_results(
        self, doctor_user, doctor_user_2, patient_user
    ):
        """FR-D-1: doctor sees results for patients assigned to them."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        tr1 = _make_result(patient, "CBC")

        other = _make_patient_user("p_qs_d2")
        other_patient = other.profile.patient_record
        other_patient.assigned_doctor = doctor_user_2.profile
        other_patient.save()
        tr2 = _make_result(other_patient, "Urinalysis")

        qs = self.tra.get_queryset(_make_request(self.factory, doctor_user))
        assert tr1 in qs
        assert tr2 not in qs

    def test_doctor_sees_results_they_ordered_even_if_patient_unassigned(
        self, doctor_user, patient_user
    ):
        """
        A doctor who ordered a test must see it even when the patient is
        not (or no longer) assigned to them.  This is the real-world case
        where a test was ordered before the patient was formally assigned,
        or the patient was later reassigned to a different doctor.
        """
        patient = patient_user.profile.patient_record
        # Patient NOT assigned to doctor_user
        assert patient.assigned_doctor != doctor_user.profile

        tr = _make_result(
            patient,
            "Unassigned CBC",
            ordering_doctor=doctor_user.profile,
        )
        qs = self.tra.get_queryset(_make_request(self.factory, doctor_user))
        assert tr in qs

    def test_doctor_does_not_see_other_doctors_ordered_unassigned_results(
        self, doctor_user, doctor_user_2, patient_user
    ):
        """
        A doctor must NOT see a result that was ordered by a different
        doctor for a patient not assigned to them.
        """
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user_2.profile
        patient.save()
        tr = _make_result(
            patient,
            "Other Dr CBC",
            ordering_doctor=doctor_user_2.profile,
        )
        qs = self.tra.get_queryset(_make_request(self.factory, doctor_user))
        assert tr not in qs

    def test_patient_sees_only_own_results(self, patient_user):
        """FR-P-1 / FR-P-3: patient sees only their own results."""
        my_patient = patient_user.profile.patient_record
        my_result = _make_result(my_patient, "CBC")

        other = _make_patient_user("p_qs_other")
        other_result = _make_result(other.profile.patient_record, "X-Ray")

        qs = self.tra.get_queryset(_make_request(self.factory, patient_user))
        assert my_result in qs
        assert other_result not in qs

    def test_nurse_sees_all_results(self, nurse_user, patient_user):
        """Nurse has read-only access to all test results."""
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        qs = self.tra.get_queryset(_make_request(self.factory, nurse_user))
        assert tr in qs

    def test_pharmacy_sees_no_results(self, pharmacy_user, patient_user):
        """Pharmacy has no access to test results."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "CBC")
        qs = self.tra.get_queryset(_make_request(self.factory, pharmacy_user))
        assert qs.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Admin permission tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestTestResultAdminPermissions:
    """has_add/change/delete/view/module_permission per role."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.tra = TestResultAdmin(TestResult, self.site)

    def _req(self, user):
        return _make_request(self.factory, user)

    # module permission
    def test_admin_has_module_permission(self, admin_user):
        assert self.tra.has_module_permission(self._req(admin_user))

    def test_doctor_has_module_permission(self, doctor_user):
        assert self.tra.has_module_permission(self._req(doctor_user))

    def test_nurse_has_module_permission(self, nurse_user):
        assert self.tra.has_module_permission(self._req(nurse_user))

    def test_patient_has_module_permission(self, patient_user):
        assert self.tra.has_module_permission(self._req(patient_user))

    def test_pharmacy_has_no_module_permission(self, pharmacy_user):
        assert not self.tra.has_module_permission(self._req(pharmacy_user))

    # add permission
    def test_admin_can_add(self, admin_user):
        assert self.tra.has_add_permission(self._req(admin_user))

    def test_doctor_can_add(self, doctor_user):
        assert self.tra.has_add_permission(self._req(doctor_user))

    def test_nurse_cannot_add(self, nurse_user):
        assert not self.tra.has_add_permission(self._req(nurse_user))

    def test_patient_cannot_add(self, patient_user):
        assert not self.tra.has_add_permission(self._req(patient_user))

    # change permission
    def test_admin_can_change(self, admin_user):
        assert self.tra.has_change_permission(self._req(admin_user))

    def test_doctor_can_change_assigned_patient_result(self, doctor_user, patient_user):
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        tr = _make_result(patient, "CBC")
        assert self.tra.has_change_permission(self._req(doctor_user), tr)

    def test_doctor_cannot_change_unassigned_patient_result(
        self, doctor_user, doctor_user_2, patient_user
    ):
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user_2.profile
        patient.save()
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_change_permission(self._req(doctor_user), tr)

    def test_nurse_cannot_change(self, nurse_user, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_change_permission(self._req(nurse_user), tr)

    def test_patient_cannot_change(self, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_change_permission(self._req(patient_user), tr)

    # delete permission
    def test_admin_can_delete(self, admin_user):
        assert self.tra.has_delete_permission(self._req(admin_user))

    def test_doctor_cannot_delete(self, doctor_user, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_delete_permission(self._req(doctor_user), tr)

    def test_nurse_cannot_delete(self, nurse_user, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_delete_permission(self._req(nurse_user), tr)

    def test_patient_cannot_delete(self, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert not self.tra.has_delete_permission(self._req(patient_user), tr)

    # view permission
    def test_admin_can_view(self, admin_user):
        assert self.tra.has_view_permission(self._req(admin_user))

    def test_patient_can_view_own_result(self, patient_user):
        patient = patient_user.profile.patient_record
        tr = _make_result(patient, "CBC")
        assert self.tra.has_view_permission(self._req(patient_user), tr)

    def test_patient_cannot_view_other_result(self, patient_user):
        """FR-P-3: patients cannot view other patients' results."""
        other = _make_patient_user("p_perm_other")
        tr = _make_result(other.profile.patient_record, "CBC")
        assert not self.tra.has_view_permission(self._req(patient_user), tr)


# ─────────────────────────────────────────────────────────────────────────────
# 6. HTTP changelist / integration tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.admin
class TestTestResultAdminHTTP:
    """HTTP-level tests against the real Django admin changelist."""

    URL = "/admin/core/testresult/"

    def setup_method(self):
        self.client = Client()

    def test_admin_changelist_loads(self, admin_user):
        self.client.force_login(admin_user)
        assert self.client.get(self.URL).status_code == 200

    def test_doctor_changelist_loads(self, doctor_user):
        self.client.force_login(doctor_user)
        assert self.client.get(self.URL).status_code == 200

    def test_patient_changelist_loads(self, patient_user):
        """FR-P-1: patient can reach their test results page."""
        self.client.force_login(patient_user)
        assert self.client.get(self.URL).status_code == 200

    def test_nurse_changelist_loads(self, nurse_user):
        self.client.force_login(nurse_user)
        assert self.client.get(self.URL).status_code == 200

    def test_pharmacy_redirected_or_forbidden(self, pharmacy_user):
        """Pharmacy has no module permission."""
        self.client.force_login(pharmacy_user)
        response = self.client.get(self.URL)
        assert response.status_code in (302, 403)

    def test_admin_sees_result_in_changelist(self, admin_user, patient_user):
        patient = patient_user.profile.patient_record
        _make_result(patient, "Thyroid Panel")
        self.client.force_login(admin_user)
        response = self.client.get(self.URL)
        assert response.status_code == 200
        assert "Thyroid Panel" in response.content.decode()

    def test_patient_sees_only_own_results(self, patient_user):
        """FR-P-1 / FR-P-3 via HTTP."""
        my_patient = patient_user.profile.patient_record
        _make_result(my_patient, "My CBC")

        other = _make_patient_user("p_http_other2")
        _make_result(other.profile.patient_record, "Other CBC")

        self.client.force_login(patient_user)
        content = self.client.get(self.URL).content.decode()
        assert "My CBC" in content
        assert "Other CBC" not in content

    def test_doctor_sees_only_assigned_patient_results(
        self, doctor_user, doctor_user_2, patient_user
    ):
        """FR-D-1 via HTTP."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()
        _make_result(patient, "D1 CBC")

        other = _make_patient_user("p_http_d2")
        other_patient = other.profile.patient_record
        other_patient.assigned_doctor = doctor_user_2.profile
        other_patient.save()
        _make_result(other_patient, "D2 Lipid")

        self.client.force_login(doctor_user)
        content = self.client.get(self.URL).content.decode()
        assert "D1 CBC" in content
        assert "D2 Lipid" not in content

    def test_status_filter(self, admin_user, patient_user):
        """?status=normal returns only normal results."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "Normal Test", status="normal")
        _make_result(patient, "Critical Test", status="critical")

        self.client.force_login(admin_user)
        content = self.client.get(self.URL, {"status": "normal"}).content.decode()
        assert "Normal Test" in content
        assert "Critical Test" not in content

    def test_test_type_filter(self, admin_user, patient_user):
        """?test_type=urinalysis returns only urinalysis results."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "Urine Test", test_type="urinalysis")
        _make_result(patient, "Blood Test", test_type="blood_panel")

        self.client.force_login(admin_user)
        content = self.client.get(
            self.URL, {"test_type": "urinalysis"}
        ).content.decode()
        assert "Urine Test" in content
        assert "Blood Test" not in content

    def test_search_by_test_name(self, admin_user, patient_user):
        """Admin can search results by test name."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "Unique Glucose Test")

        self.client.force_login(admin_user)
        content = self.client.get(self.URL, {"q": "Unique Glucose"}).content.decode()
        assert "Unique Glucose Test" in content

    def test_doctor_add_form_loads(self, doctor_user):
        """Doctor can access the add form."""
        self.client.force_login(doctor_user)
        assert self.client.get(self.URL + "add/").status_code == 200

    def test_changelist_no_errors_for_allowed_roles(
        self, admin_user, doctor_user, nurse_user, patient_user
    ):
        """Changelist returns HTTP 200 for every role with access."""
        for user in [admin_user, doctor_user, nurse_user, patient_user]:
            self.client.force_login(user)
            resp = self.client.get(self.URL)
            assert resp.status_code == 200, (
                f"Got {resp.status_code} for role " f"'{user.profile.role}'"
            )

    def test_results_ordered_newest_first_in_changelist(self, admin_user, patient_user):
        """FR-D-3: changelist shows newest results at the top."""
        patient = patient_user.profile.patient_record
        _make_result(patient, "Older Test", test_date=TWO_DAYS_AGO)
        _make_result(patient, "Newer Test", test_date=YESTERDAY)

        self.client.force_login(admin_user)
        content = self.client.get(self.URL).content.decode()
        pos_newer = content.find("Newer Test")
        pos_older = content.find("Older Test")
        assert (
            pos_newer < pos_older
        ), "Newer test should appear before older test in the list"
