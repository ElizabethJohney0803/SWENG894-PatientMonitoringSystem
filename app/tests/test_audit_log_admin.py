"""
Tests for AuditLogAdmin — PBI-S4-16
TC-S4-055 — TC-S4-059

FR-P-8, FR-AA-3
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from core.models import UserProfile, AuditLog
from core.admin import AuditLogAdmin


@pytest.fixture
def rf():
    return RequestFactory()


def _make_request(rf, user):
    req = rf.get("/admin/core/auditlog/")
    req.user = user
    return req


@pytest.mark.django_db
class TestAuditLogAdminListDisplay:
    """TC-S4-055 — list_display shows required columns (AC-16.1)."""

    def test_list_display_contains_required_fields(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        required = {
            "timestamp",
            "user",
            "action",
            "model_name",
            "object_id",
            "object_repr",
            "ip_address",
        }
        assert required <= set(ma.list_display)


@pytest.mark.django_db
class TestAuditLogAdminFilters:
    """TC-S4-056 — list_filter and date_hierarchy configured (AC-16.2)."""

    def test_list_filter_includes_action(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        assert "action" in ma.list_filter

    def test_list_filter_includes_user(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        assert "user" in ma.list_filter

    def test_list_filter_includes_model_name(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        assert "model_name" in ma.list_filter

    def test_date_hierarchy_is_timestamp(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        assert ma.date_hierarchy == "timestamp"


@pytest.mark.django_db
class TestAuditLogAdminReadOnly:
    """TC-S4-057 — All fields are read-only and no add/change/delete (AC-16.3)."""

    def test_all_significant_fields_readonly(self, create_groups):
        admin_u = User.objects.create_user(
            username="al_admin_ro",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=admin_u, role="admin")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        required = {
            "timestamp",
            "user",
            "action",
            "model_name",
            "object_id",
            "object_repr",
            "ip_address",
            "changes_summary",
        }
        assert required <= set(ma.readonly_fields)

    def test_has_add_permission_false(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_admin_add",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="admin")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_add_permission(request) is False

    def test_has_change_permission_false(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_admin_chg",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="admin")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_change_permission(request) is False

    def test_has_delete_permission_false(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_admin_del",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="admin")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_delete_permission(request) is False


@pytest.mark.django_db
class TestAuditLogAdminAccessControl:
    """TC-S4-058 — Non-admin roles receive HTTP 403 (AC-16.4)."""

    def test_admin_role_has_module_permission(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_admin_mod",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="admin")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_module_permission(request) is True

    def test_doctor_role_denied_module_permission(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_doctor_mod",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="doctor", license_number="MD777")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_module_permission(request) is False

    def test_nurse_role_denied_module_permission(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_nurse_mod",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="nurse", license_number="RN777")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_module_permission(request) is False

    def test_pharmacy_role_denied_module_permission(self, rf, create_groups):
        user = User.objects.create_user(
            username="al_pharma_mod",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=user, role="pharmacy", license_number="PH777")
        ma = AuditLogAdmin(AuditLog, AdminSite())
        request = _make_request(rf, user)
        assert ma.has_module_permission(request) is False

    def test_non_admin_http_403(self, create_groups):
        """Non-admin requesting audit log URL should get 403."""
        from django.test import Client

        nurse = User.objects.create_user(
            username="al_nurse_403",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=nurse, role="nurse", license_number="RN888")
        client = Client()
        client.login(username="al_nurse_403", password="testpass")
        response = client.get("/admin/core/auditlog/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAuditLogAdminOrdering:
    """TC-S4-059 — Default ordering is timestamp descending (AC-16.5)."""

    def test_ordering_is_timestamp_desc(self):
        ma = AuditLogAdmin(AuditLog, AdminSite())
        assert "-timestamp" in ma.ordering

    def test_queryset_ordered_newest_first(self, rf, create_groups):
        admin_u = User.objects.create_user(
            username="al_admin_ord",
            password="testpass",
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(user=admin_u, role="admin")

        # Create three log entries
        e1 = AuditLog.objects.create(
            action="read", model_name="Patient", object_repr="p1"
        )
        e2 = AuditLog.objects.create(
            action="create", model_name="Medication", object_repr="m1"
        )
        e3 = AuditLog.objects.create(
            action="update", model_name="Patient", object_repr="p2"
        )

        request = _make_request(rf, admin_u)
        ma = AuditLogAdmin(AuditLog, AdminSite())
        qs = ma.get_queryset(request)
        items = list(qs)

        # Most recently created should be first
        assert items[0].pk == e3.pk
        assert items[-1].pk == e1.pk
