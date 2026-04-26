"""
Tests for Admin Dashboard Statistics — PBI-S4-12 (Stretch)
TC-S4-049 — TC-S4-050

FR-A-12 / AC-12.1 / AC-12.2
"""

import pytest
from datetime import date
from django.contrib.auth.models import User
from django.test import Client, RequestFactory
from core.models import UserProfile, Patient, Medication, AuditLog


@pytest.mark.django_db
class TestAdminDashboardStatisticsPanelVisible:
    """AC-12.1 — Admin dashboard shows total counts for patients, doctors, nurses."""

    @pytest.fixture(autouse=True)
    def setup(self, create_groups):
        # Create admin user
        self.admin_u = User.objects.create_user(
            username="dash_admin",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=self.admin_u, role="admin")

        # Create several users of different roles
        dr = User.objects.create_user(
            username="dash_dr1", password="testpass", is_staff=True
        )
        UserProfile.objects.create(user=dr, role="doctor", license_number="MD_D1")

        nu = User.objects.create_user(
            username="dash_nu1", password="testpass", is_staff=True
        )
        UserProfile.objects.create(user=nu, role="nurse", license_number="RN_N1")

        ph = User.objects.create_user(
            username="dash_ph1", password="testpass", is_staff=True
        )
        UserProfile.objects.create(user=ph, role="pharmacy", license_number="PH_P1")

    def test_admin_can_access_index(self):
        """Admin role can request the admin index page (HTTP 200)."""
        client = Client()
        client.login(username="dash_admin", password="testpass")
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_admin_stats_context_injected(self):
        """admin_stats key is injected into the admin index context for admin users."""
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = self.admin_u

        # Ensure the site class is the custom one
        assert isinstance(admin_site, CustomAdminSite)

        # Build a minimal session/middleware state expected by index()
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()

        response = admin_site.index(request)
        # The context_data attribute may not exist on TemplateResponse directly;
        # instead check via context_data or rendered content
        # The stats dict is in extra_context — we access via response.context_data
        assert hasattr(response, "context_data")
        stats = response.context_data.get("admin_stats")
        assert stats is not None

    def test_stats_contain_required_keys(self):
        """Stats dict has all required count keys."""
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = self.admin_u

        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()

        response = admin_site.index(request)
        stats = response.context_data.get("admin_stats", {})
        required_keys = {
            "total_patients",
            "total_doctors",
            "total_nurses",
            "total_pharmacy",
            "pending_medications",
            "recent_audit_logs",
        }
        assert required_keys <= set(stats.keys())

    def test_doctor_count_correct(self):
        """total_doctors count reflects actual doctor profiles."""
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        expected = UserProfile.objects.filter(role="doctor").count()

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = self.admin_u
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()
        response = admin_site.index(request)
        stats = response.context_data.get("admin_stats", {})
        assert stats["total_doctors"] == expected

    def test_nurse_count_correct(self):
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        expected = UserProfile.objects.filter(role="nurse").count()

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = self.admin_u
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()
        response = admin_site.index(request)
        stats = response.context_data.get("admin_stats", {})
        assert stats["total_nurses"] == expected


@pytest.mark.django_db
class TestAdminDashboardRecentAuditLogs:
    """AC-12.2 — Dashboard shows 5 most recent audit log entries."""

    @pytest.fixture(autouse=True)
    def setup(self, create_groups):
        self.admin_u = User.objects.create_user(
            username="dash_audit_admin",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=self.admin_u, role="admin")

        # Create 6 audit log entries — only 5 should appear
        for i in range(6):
            AuditLog.objects.create(
                action="read",
                model_name="Patient",
                object_repr=f"Patient {i}",
                object_id=str(i),
            )

    def test_recent_audit_logs_at_most_5(self):
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = self.admin_u
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()
        response = admin_site.index(request)
        stats = response.context_data.get("admin_stats", {})
        recent = list(stats.get("recent_audit_logs", []))
        assert len(recent) <= 5

    def test_non_admin_stats_not_injected(self, create_groups):
        """Non-admin users do not get the admin_stats context variable."""
        from core.admin import CustomAdminSite
        from django.contrib.admin import site as admin_site

        doctor = User.objects.create_user(
            username="dash_dr_no_stats",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(user=doctor, role="doctor", license_number="MD_NO")

        rf = RequestFactory()
        request = rf.get("/admin/")
        request.user = doctor
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()
        response = admin_site.index(request)
        stats = response.context_data.get("admin_stats")
        assert stats is None
