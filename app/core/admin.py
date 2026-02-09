from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline admin for user profile."""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"

    fieldsets = (
        ("Role Information", {"fields": ("role", "department")}),
        ("Professional Details", {"fields": ("license_number", "phone")}),
    )


class UserAdmin(BaseUserAdmin):
    """Custom user admin with profile inline."""

    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for user profiles."""

    list_display = ("user", "role", "department", "license_number", "created_at")
    list_filter = ("role", "department", "created_at")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "license_number",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        ("Role & Department", {"fields": ("role", "department")}),
        ("Professional Details", {"fields": ("license_number", "phone")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        """Filter profiles based on user role."""
        qs = super().get_queryset(request)

        # Admin users can see all profiles
        if request.user.is_superuser:
            return qs

        # Regular users can only see their own profile
        return qs.filter(user=request.user)

    def has_add_permission(self, request):
        """Only superusers can add new profiles."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete profiles."""
        return request.user.is_superuser


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
