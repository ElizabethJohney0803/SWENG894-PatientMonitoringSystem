from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404


class RoleBasedAdminMixin:
    """Base mixin for role-based admin access control."""

    def get_queryset(self, request):
        """Filter queryset based on user role."""
        qs = super().get_queryset(request)

        # Always allow superusers to see everything
        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, "profile"):
            return qs.none()

        user_role = request.user.profile.role

        # Admins see everything
        if user_role == "admin":
            return qs

        # Apply role-specific filtering
        return self.filter_queryset_by_role(request, qs, user_role)

    def filter_queryset_by_role(self, request, queryset, role):
        """Override this method to implement role-specific filtering."""
        return queryset

    def has_view_permission(self, request, obj=None):
        """Check view permission based on role."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has profile
        if not hasattr(request.user, "profile"):
            return False

        # For users with valid roles, bypass Django's default permission system
        user_role = request.user.profile.role
        if user_role in ["admin", "doctor", "nurse", "pharmacy", "patient"]:
            return self.check_role_permission(request, obj, "view")

        # Fall back to Django's permission system for users without roles
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        """Check change permission based on role."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has profile
        if not hasattr(request.user, "profile"):
            return False

        # For users with valid roles, bypass Django's default permission system
        user_role = request.user.profile.role
        if user_role in ["admin", "doctor", "nurse", "pharmacy", "patient"]:
            return self.check_role_permission(request, obj, "change")

        # Fall back to Django's permission system for users without roles
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        """Check add permission based on role."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has profile
        if not hasattr(request.user, "profile"):
            return False

        # For users with valid roles, bypass Django's default permission system
        user_role = request.user.profile.role
        if user_role in ["admin", "doctor", "nurse", "pharmacy", "patient"]:
            return self.check_role_permission(request, None, "add")

        # Fall back to Django's permission system for users without roles
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission based on role."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has profile
        if not hasattr(request.user, "profile"):
            return False

        # For users with valid roles, bypass Django's default permission system
        user_role = request.user.profile.role
        if user_role in ["admin", "doctor", "nurse", "pharmacy", "patient"]:
            return self.check_role_permission(request, obj, "delete")

        # Fall back to Django's permission system for users without roles
        return super().has_delete_permission(request, obj)
        if request.user.is_superuser:
            return True
        return self.check_role_permission(request, obj, "delete")

    def check_role_permission(self, request, obj, action):
        """Override this method to implement role-specific permission checks."""
        if not hasattr(request.user, "profile"):
            return False
        return True


class PatientAccessMixin(RoleBasedAdminMixin):
    """Mixin for models that patients should only see their own data."""

    def filter_queryset_by_role(self, request, queryset, role):
        if role == "patient":
            # Handle different model types - some have user field, some have user_profile
            model = queryset.model
            if hasattr(model, "user_profile"):
                # Patient model - filter by user_profile
                return queryset.filter(user_profile=request.user.profile)
            elif hasattr(model, "user"):
                # Models with direct user relationship
                return queryset.filter(user=request.user)
            else:
                # Fallback - return empty queryset if relationship unclear
                return queryset.none()
        return queryset

    def check_role_permission(self, request, obj, action):
        if not super().check_role_permission(request, obj, action):
            return False

        user_role = request.user.profile.role

        # Patients can only access their own records
        if user_role == "patient":
            # Patients cannot delete their own Patient records
            if action == "delete":
                return False

            if obj:
                # Check if object belongs to the patient
                if hasattr(obj, "user_profile"):
                    return obj.user_profile == request.user.profile
                elif hasattr(obj, "user"):
                    return obj.user == request.user
                else:
                    return False
            # For add operations, patients can only add to themselves
            if action == "add":
                return True  # Will be filtered during save

        return True

    def has_add_permission(self, request):
        """Check add permission with admin role support."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Allow users with admin role
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True

        # Fall back to mixin permission check
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission with admin role support."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Allow users with admin role
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True

        # Fall back to mixin permission check
        return super().has_delete_permission(request, obj)


class MedicalStaffMixin(RoleBasedAdminMixin):
    """Mixin for medical staff access control."""

    def check_role_permission(self, request, obj, action):
        if not super().check_role_permission(request, obj, action):
            return False

        user_role = request.user.profile.role

        # Only medical staff and admins can perform these actions
        allowed_roles = ["doctor", "nurse", "pharmacy", "admin"]
        return user_role in allowed_roles


class DoctorOnlyMixin(RoleBasedAdminMixin):
    """Mixin for doctor-only operations."""

    def check_role_permission(self, request, obj, action):
        if not super().check_role_permission(request, obj, action):
            return False

        user_role = request.user.profile.role
        return user_role in ["doctor", "admin"]


class AdminOnlyMixin(RoleBasedAdminMixin):
    """Mixin for admin-only operations."""

    def check_role_permission(self, request, obj, action):
        # Always allow superusers
        if request.user.is_superuser:
            return True

        if not super().check_role_permission(request, obj, action):
            return False

        # Check if user has admin role
        if hasattr(request.user, "profile"):
            return request.user.profile.role == "admin"

        return False
