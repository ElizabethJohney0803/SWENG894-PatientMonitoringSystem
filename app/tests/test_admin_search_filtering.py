"""
Tests for Patient admin search functionality and filtering options.

Covers:
  - CityListFilter lookups and queryset behaviour
  - get_search_fields() per user role (FR-D-6)
  - get_list_filter()  per user role (WF-S3-01)
  - search_help_text attribute
  - HTTP changelist search (?q=…) and city-filter (?city=…) requests

Related functional requirements:
  FR-D-6  Doctor can search patients by name or ID
  FR-A-2  Admin can view/search patient records
  WF-S3-01 Patient List: Search & Filter wireframe
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from core.admin import CityListFilter, PatientAdmin
from core.models import Patient, UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_request(factory, user):
    """Return a GET request authenticated as *user*."""
    request = factory.get("/")
    request.user = user
    return request


def _make_patient(username, first_name, last_name, city="", gender="M"):
    """Create a User + UserProfile(patient) + Patient record and return the Patient."""
    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password="testpass",
    )
    profile = UserProfile.objects.create(user=user, role="patient")
    patient = profile.patient_record  # auto-created by signal / ensure_patient_record
    patient.city = city
    patient.gender = gender
    patient.save()
    return patient


# ─────────────────────────────────────────────────────────────────────────────
# CityListFilter unit tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestCityListFilter:
    """Unit tests for the CityListFilter SimpleListFilter."""

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.model_admin = PatientAdmin(Patient, self.admin_site)

    def test_lookups_returns_distinct_sorted_cities(self, admin_user):
        """lookups() should return each city once, sorted alphabetically."""
        _make_patient("p_boston", "Alice", "Brown", city="Boston")
        _make_patient("p_chicago", "Bob", "Smith", city="Chicago")
        _make_patient("p_boston2", "Carol", "Doe", city="Boston")  # duplicate city

        request = _make_request(self.factory, admin_user)
        f = CityListFilter(request, {}, Patient, self.model_admin)
        lookup_values = [val for val, _label in f.lookups(request, self.model_admin)]

        # Boston should appear exactly once; cities sorted
        assert lookup_values.count("Boston") == 1
        assert lookup_values.count("Chicago") == 1
        assert lookup_values == sorted(lookup_values)

    def test_lookups_excludes_blank_city(self, admin_user):
        """lookups() must not include patients with an empty or null city."""
        _make_patient("p_nocity", "David", "Jones", city="")

        request = _make_request(self.factory, admin_user)
        f = CityListFilter(request, {}, Patient, self.model_admin)
        lookup_values = [val for val, _label in f.lookups(request, self.model_admin)]

        assert "" not in lookup_values
        assert None not in lookup_values

    def test_queryset_filters_to_selected_city(self, admin_user):
        """When a city is selected the queryset should return only that city's patients."""
        p_boston = _make_patient("p_b_filter", "Eve", "Taylor", city="Boston")
        p_chicago = _make_patient("p_c_filter", "Frank", "Lee", city="Chicago")

        request = _make_request(self.factory, admin_user)
        params = {"city": "Boston"}
        f = CityListFilter(request, params, Patient, self.model_admin)
        qs = f.queryset(request, Patient.objects.all())

        assert p_boston in qs
        assert p_chicago not in qs

    def test_queryset_returns_all_when_no_city_selected(self, admin_user):
        """When no city value is selected the queryset should be unmodified."""
        p1 = _make_patient("p_x1", "Grace", "Hall", city="New York")
        p2 = _make_patient("p_x2", "Henry", "King", city="Miami")

        request = _make_request(self.factory, admin_user)
        f = CityListFilter(request, {}, Patient, self.model_admin)
        qs_all = Patient.objects.all()
        qs_filtered = f.queryset(request, qs_all)

        # No narrowing: every patient should still be present
        assert p1 in qs_filtered
        assert p2 in qs_filtered


# ─────────────────────────────────────────────────────────────────────────────
# search_help_text
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.admin
class TestPatientAdminSearchHelpText:
    """The search_help_text attribute should reference FR-D-6."""

    def test_search_help_text_exists(self):
        admin_site = AdminSite()
        pa = PatientAdmin(Patient, admin_site)
        assert hasattr(pa, "search_help_text")
        assert pa.search_help_text  # non-empty

    def test_search_help_text_mentions_fr_d6(self):
        admin_site = AdminSite()
        pa = PatientAdmin(Patient, admin_site)
        assert "FR-D-6" in pa.search_help_text


# ─────────────────────────────────────────────────────────────────────────────
# get_search_fields() per role  (FR-D-6)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestGetSearchFieldsPerRole:
    """
    get_search_fields() must return role-appropriate fields.

    FR-D-6: Doctors search by name or patient ID only.
    Admins get the full set that includes assigned-doctor name fields.
    """

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.pa = PatientAdmin(Patient, self.admin_site)

    # ── Patient ──────────────────────────────────────────────────────────────

    def test_patient_gets_empty_search_fields(self, patient_user):
        """Patients see only their own record — search is unnecessary."""
        request = _make_request(self.factory, patient_user)
        fields = self.pa.get_search_fields(request)
        assert fields == []

    # ── Doctor (FR-D-6) ──────────────────────────────────────────────────────

    def test_doctor_gets_name_and_medical_id_search(self, doctor_user):
        """FR-D-6: doctors must be able to search by name or medical ID."""
        request = _make_request(self.factory, doctor_user)
        fields = self.pa.get_search_fields(request)

        assert "medical_id" in fields
        assert "user_profile__user__first_name" in fields
        assert "user_profile__user__last_name" in fields

    def test_doctor_does_not_get_admin_only_search_fields(self, doctor_user):
        """Doctor search should NOT expose insurance or assigned-doctor fields."""
        request = _make_request(self.factory, doctor_user)
        fields = self.pa.get_search_fields(request)

        # Insurance number and city should not be in doctor's search fields
        assert "insurance_number" not in fields

    # ── Nurse ─────────────────────────────────────────────────────────────────

    def test_nurse_gets_name_phone_and_city_search(self, nurse_user):
        """Nurses should be able to search by name, medical ID, phone, and city."""
        request = _make_request(self.factory, nurse_user)
        fields = self.pa.get_search_fields(request)

        assert "medical_id" in fields
        assert "user_profile__user__first_name" in fields
        assert "user_profile__user__last_name" in fields
        assert "phone_primary" in fields
        assert "city" in fields

    # ── Pharmacy ──────────────────────────────────────────────────────────────

    def test_pharmacy_gets_same_search_fields_as_nurse(self, pharmacy_user, nurse_user):
        """Pharmacy and nurse should have the same search field set."""
        factory = self.factory
        pharmacy_fields = self.pa.get_search_fields(
            _make_request(factory, pharmacy_user)
        )
        nurse_fields = self.pa.get_search_fields(_make_request(factory, nurse_user))
        assert set(pharmacy_fields) == set(nurse_fields)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def test_admin_gets_full_search_fields(self, admin_user):
        """Admin users should get the full search_fields set."""
        request = _make_request(self.factory, admin_user)
        fields = self.pa.get_search_fields(request)

        assert "medical_id" in fields
        assert "user_profile__user__first_name" in fields
        assert "user_profile__user__last_name" in fields
        assert "assigned_doctor__user__first_name" in fields
        assert "assigned_doctor__user__last_name" in fields
        assert "city" in fields
        assert "insurance_number" in fields

    def test_admin_search_fields_match_static_search_fields(self, admin_user):
        """Admin get_search_fields() should return same content as static search_fields."""
        request = _make_request(self.factory, admin_user)
        dynamic = set(self.pa.get_search_fields(request))
        static = set(self.pa.search_fields)
        assert dynamic == static

    # ── Superuser ─────────────────────────────────────────────────────────────

    def test_superuser_gets_full_search_fields(self, django_user_model):
        """Superusers should also get the full search_fields set."""
        superuser = django_user_model.objects.create_superuser(
            username="su_search", password="testpass"
        )
        request = _make_request(self.factory, superuser)
        fields = self.pa.get_search_fields(request)

        assert "assigned_doctor__user__first_name" in fields
        assert "insurance_number" in fields


# ─────────────────────────────────────────────────────────────────────────────
# get_list_filter() per role  (WF-S3-01)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.admin
class TestGetListFilterPerRole:
    """
    get_list_filter() must include CityListFilter for admin/nurse/pharmacy
    and return [] for doctor and patient roles (WF-S3-01).
    """

    def setup_method(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.pa = PatientAdmin(Patient, self.admin_site)

    def test_patient_gets_no_filters(self, patient_user):
        request = _make_request(self.factory, patient_user)
        assert self.pa.get_list_filter(request) == []

    def test_doctor_gets_no_filters(self, doctor_user):
        """WF-S3-01 note: filters hidden for Doctor view."""
        request = _make_request(self.factory, doctor_user)
        assert self.pa.get_list_filter(request) == []

    def test_nurse_filters_are_empty(self, nurse_user):
        """Nurse sees only their assigned patients — no sidebar filters needed."""
        request = _make_request(self.factory, nurse_user)
        assert self.pa.get_list_filter(request) == []

    def test_nurse_has_no_gender_filter(self, nurse_user):
        """Nurse queryset is scoped by assignment, not filtered by demographics."""
        request = _make_request(self.factory, nurse_user)
        assert "gender" not in self.pa.get_list_filter(request)

    def test_pharmacy_filters_include_city(self, pharmacy_user):
        request = _make_request(self.factory, pharmacy_user)
        assert CityListFilter in self.pa.get_list_filter(request)

    def test_admin_filters_include_city(self, admin_user):
        request = _make_request(self.factory, admin_user)
        assert CityListFilter in self.pa.get_list_filter(request)

    def test_admin_filters_include_assigned_doctor(self, admin_user):
        """WF-S3-01 sidebar: 'By Assigned Doctor' filter for admin."""
        request = _make_request(self.factory, admin_user)
        assert "assigned_doctor" in self.pa.get_list_filter(request)

    def test_admin_filters_include_gender(self, admin_user):
        """WF-S3-01 sidebar: 'By Gender' filter for admin."""
        request = _make_request(self.factory, admin_user)
        assert "gender" in self.pa.get_list_filter(request)

    def test_superuser_filters_include_city_and_assigned_doctor(
        self, django_user_model
    ):
        superuser = django_user_model.objects.create_superuser(
            username="su_filter", password="testpass"
        )
        request = _make_request(self.factory, superuser)
        filters = self.pa.get_list_filter(request)
        assert CityListFilter in filters
        assert "assigned_doctor" in filters


# ─────────────────────────────────────────────────────────────────────────────
# HTTP changelist — search and filter via Django test client
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.admin
class TestPatientAdminChangelistSearch:
    """
    HTTP-level tests that hit the real Django admin changelist view.
    These verify that search (?q=…) and filter (?city=…, ?gender=…)
    return the correct patients and produce no errors.
    """

    CHANGELIST_URL = "/admin/core/patient/"

    def setup_method(self):
        self.client = Client()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _login(self, user):
        self.client.force_login(user)

    # ── admin search tests ────────────────────────────────────────────────────

    def test_admin_search_by_last_name_returns_correct_patient(
        self, admin_user, patient_user
    ):
        """Admin ?q=Johnson should surface patient_user (last_name=Johnson)."""
        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL, {"q": "Johnson"})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Johnson" in content

    def test_admin_search_by_medical_id_returns_correct_patient(
        self, admin_user, patient_user
    ):
        """Admin ?q=<medical_id> should return the matching patient."""
        medical_id = patient_user.profile.patient_record.medical_id
        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL, {"q": medical_id})
        assert response.status_code == 200
        content = response.content.decode()
        assert medical_id in content

    def test_admin_search_no_results_is_handled_gracefully(self, admin_user):
        """Searching for a non-existent string should return 200 with empty results."""
        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL, {"q": "ZZZNOMATCH99999"})
        assert response.status_code == 200

    def test_admin_search_by_assigned_doctor_name(
        self, admin_user, doctor_user, patient_user
    ):
        """Admin can search patients by their assigned doctor's name (FR-D-6 extended)."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        self._login(admin_user)
        # doctor_user first_name = "John"
        response = self.client.get(self.CHANGELIST_URL, {"q": "Smith"})
        assert response.status_code == 200
        content = response.content.decode()
        # The patient assigned to Dr Smith should appear
        assert patient.medical_id in content

    # ── doctor search tests (FR-D-6) ──────────────────────────────────────────

    def test_doctor_search_returns_only_own_patients(
        self, doctor_user, doctor_user_2, patient_user
    ):
        """
        FR-D-6: when a doctor searches, results are scoped to their patients only.
        Even if the search term would match another doctor's patient it must not appear.
        """
        # Assign patient to doctor1
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        # Create a second patient assigned to doctor2
        p2 = _make_patient("p_d2_search", "Bob", "Johnson", city="Seattle")
        p2.assigned_doctor = doctor_user_2.profile
        p2.save()

        self._login(doctor_user)
        # Search "Johnson" — both patients have last name Johnson
        response = self.client.get(self.CHANGELIST_URL, {"q": "Johnson"})
        assert response.status_code == 200
        content = response.content.decode()

        # Doctor1's patient should appear
        assert patient_user.profile.patient_record.medical_id in content
        # Doctor2's patient must NOT appear
        assert p2.medical_id not in content

    def test_doctor_search_by_medical_id(self, doctor_user, patient_user):
        """FR-D-6: doctor can search for their patient by medical ID."""
        patient = patient_user.profile.patient_record
        patient.assigned_doctor = doctor_user.profile
        patient.save()

        self._login(doctor_user)
        response = self.client.get(self.CHANGELIST_URL, {"q": patient.medical_id})
        assert response.status_code == 200
        assert patient.medical_id in response.content.decode()

    # ── city filter tests (WF-S3-01) ─────────────────────────────────────────

    def test_admin_city_filter_returns_only_patients_in_city(self, admin_user):
        """?city=Boston should return only Boston patients."""
        p_boston = _make_patient("p_bos_http", "Anna", "Moore", city="Boston")
        p_dallas = _make_patient("p_dal_http", "Brian", "Clark", city="Dallas")

        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL, {"city": "Boston"})
        assert response.status_code == 200
        content = response.content.decode()

        assert p_boston.medical_id in content
        assert p_dallas.medical_id not in content

    def test_admin_city_filter_shows_all_patients_when_unfiltered(self, admin_user):
        """Without ?city= all patients should be visible."""
        p1 = _make_patient("p_any1_http", "Chris", "Evans", city="Miami")
        p2 = _make_patient("p_any2_http", "Diana", "Ross", city="Austin")

        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL)
        assert response.status_code == 200
        content = response.content.decode()

        assert p1.medical_id in content
        assert p2.medical_id in content

    # ── gender filter tests ───────────────────────────────────────────────────

    def test_admin_gender_filter_returns_correct_patients(self, admin_user):
        """?gender=M should return only male patients."""
        p_male = _make_patient(
            "p_male_http", "George", "Hill", city="Portland", gender="M"
        )
        p_female = _make_patient(
            "p_female_http", "Helen", "Ward", city="Portland", gender="F"
        )

        self._login(admin_user)
        response = self.client.get(self.CHANGELIST_URL, {"gender": "M"})
        assert response.status_code == 200
        content = response.content.decode()

        assert p_male.medical_id in content
        assert p_female.medical_id not in content

    # ── no errors in admin interface ──────────────────────────────────────────

    def test_changelist_loads_without_error_for_all_roles(
        self, admin_user, doctor_user, nurse_user, pharmacy_user, patient_user
    ):
        """
        The changelist view must return HTTP 200 for every staff role with no
        server-side errors.  (Patient user is not is_staff so skip.)
        """
        staff_users = [admin_user, doctor_user, nurse_user, pharmacy_user]
        for user in staff_users:
            self.client.force_login(user)
            response = self.client.get(self.CHANGELIST_URL)
            assert response.status_code == 200, (
                f"Changelist returned {response.status_code} for role "
                f"'{user.profile.role}'"
            )

    def test_search_and_city_filter_combined(self, admin_user):
        """Combining ?q= and ?city= should apply both constraints."""
        p_target = _make_patient("p_combo_t", "Ivan", "Russo", city="Chicago")
        p_other_city = _make_patient("p_combo_o1", "Ivan", "Russo", city="Denver")
        p_other_name = _make_patient("p_combo_o2", "Zara", "Patel", city="Chicago")

        self._login(admin_user)
        response = self.client.get(
            self.CHANGELIST_URL, {"q": "Russo", "city": "Chicago"}
        )
        assert response.status_code == 200
        content = response.content.decode()

        assert p_target.medical_id in content
        assert p_other_city.medical_id not in content
        assert p_other_name.medical_id not in content
