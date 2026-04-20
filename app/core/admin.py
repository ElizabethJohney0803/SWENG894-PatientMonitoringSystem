import json

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Count, Min
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    UserProfile,
    Patient,
    EmergencyContact,
    Medication,
    TestResult,
    Appointment,
    AuditLog,
)
from .mixins import PatientAccessMixin, AdminOnlyMixin


# ---------------------------------------------------------------------------
# Audit-logging helper
# ---------------------------------------------------------------------------


def _write_audit_log(request, action, obj, changes_summary=""):
    """
    Create an immutable AuditLog entry.  Silently swallows exceptions so
    that a logging failure never breaks a real request.
    """
    try:
        ip = request.META.get("REMOTE_ADDR")
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            model_name=obj.__class__.__name__,
            object_id=str(obj.pk) if obj.pk else "",
            object_repr=str(obj)[:500],
            ip_address=ip,
            changes_summary=changes_summary,
        )
    except Exception:
        pass


def _build_changes_summary(old_data: dict, new_data: dict) -> str:
    """Return a JSON string describing changed fields: {field: [old, new], ...}."""
    diff = {
        field: [old_val, new_data.get(field)]
        for field, old_val in old_data.items()
        if old_val != new_data.get(field)
    }
    return json.dumps(diff) if diff else ""


def _snapshot(obj) -> dict:
    """Capture a field-value snapshot of a model instance."""
    return {
        f.name: str(getattr(obj, f.name, ""))
        for f in obj._meta.concrete_fields
        if f.name not in ("created_at", "updated_at")
    }


class CityListFilter(admin.SimpleListFilter):
    """
    Filter sidebar panel for city — WF-S3-01 'By City'.
    Shows distinct cities drawn from actual Patient records.
    """

    title = "city"
    parameter_name = "city"

    def lookups(self, request, model_admin):
        """Return (value, label) pairs for every distinct non-blank city."""
        cities = (
            Patient.objects.exclude(city="")
            .exclude(city__isnull=True)
            .values_list("city", flat=True)
            .distinct()
            .order_by("city")
        )
        return [(city, city) for city in cities]

    def queryset(self, request, queryset):
        """Filter the changelist queryset to the selected city."""
        if self.value():
            return queryset.filter(city=self.value())
        return queryset


class PatientAdminForm(forms.ModelForm):
    """Custom form for Patient admin with proper assigned_doctor handling."""

    class Meta:
        model = Patient
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit assigned_doctor choices to only doctors
        if "assigned_doctor" in self.fields:
            self.fields["assigned_doctor"].queryset = UserProfile.objects.filter(
                role="doctor"
            )
            self.fields["assigned_doctor"].required = False


class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with role assignment."""

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        help_text="Select the user's role in the system",
        widget=forms.Select(attrs={"onchange": "toggleRequiredFields()"}),
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        help_text="Department or ward assignment (required for doctors and nurses)",
        widget=forms.TextInput(attrs={"class": "role-dependent"}),
    )
    license_number = forms.CharField(
        max_length=50,
        required=False,
        help_text="Professional license number (required for medical staff)",
        widget=forms.TextInput(attrs={"class": "role-dependent"}),
    )
    phone = forms.CharField(
        max_length=20, required=False, help_text="Contact phone number"
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    class Media:
        js = ("admin/js/role_validation.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial field visibility based on data if available
        if "data" in kwargs and kwargs["data"].get("role") == "patient":
            # For patients, remove license_number field entirely
            if "license_number" in self.fields:
                del self.fields["license_number"]

        # Add help text to role field to guide admin users
        self.fields["role"].help_text = (
            "Select role type. Fields below will be shown/hidden based on selection. "
            "Patients don't require professional credentials."
        )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        department = cleaned_data.get("department")
        license_number = cleaned_data.get("license_number")

        if not role:
            raise forms.ValidationError("Role selection is required.")

        # Skip license validation for patients
        if role == "patient":
            return cleaned_data

        # Validate required fields based on role for non-patients
        errors = {}

        if role in ["doctor", "nurse", "pharmacy"] and not license_number:
            errors["license_number"] = "License number is required for medical staff."

        if role in ["doctor", "nurse"] and not department:
            errors["department"] = "Department is required for doctors and nurses."

        if errors:
            raise forms.ValidationError(errors)

        # Ensure role is preserved in cleaned_data
        cleaned_data["role"] = role
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(user=user)

            # Set all profile fields from form data
            role = self.cleaned_data["role"]
            profile.role = role
            profile.department = self.cleaned_data.get("department", "")
            profile.phone = self.cleaned_data.get("phone", "")

            # Only set license_number for non-patients and if field exists
            if (
                role != "patient"
                and "license_number" in self.cleaned_data
                and self.cleaned_data.get("license_number")
            ):
                profile.license_number = self.cleaned_data["license_number"]
            elif role == "patient":
                # Ensure patients don't have license numbers
                profile.license_number = ""

            # Save profile - this will trigger group assignment
            profile.save()

        return user


class UserProfileInline(admin.StackedInline):
    """Inline admin for user profile."""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on role - hide license for patients."""
        base_fieldsets = [
            ("Role Information", {"fields": ("role", "department")}),
        ]

        # Determine if we're dealing with a patient
        is_patient = False
        if obj and hasattr(obj, "profile"):
            is_patient = obj.profile.role == "patient"
        elif request.POST.get("role") == "patient":
            is_patient = True

        # Add appropriate contact/professional sections
        if is_patient:
            # Patients only get contact information, no license field
            base_fieldsets.append(("Contact Information", {"fields": ("phone",)}))
        else:
            # Non-patients get professional details including license
            base_fieldsets.append(
                ("Professional Details", {"fields": ("license_number", "phone")})
            )

        return base_fieldsets

    def get_readonly_fields(self, request, obj=None):
        """Make role field readonly for non-admins."""
        readonly_fields = []

        if not request.user.is_superuser and hasattr(request.user, "profile"):
            if request.user.profile.role != "admin":
                readonly_fields.append("role")

        return readonly_fields

    def get_exclude(self, request, obj=None):
        """Exclude license field for patients."""
        exclude = []

        # Determine if we're dealing with a patient
        is_patient = False
        if obj and hasattr(obj, "profile"):
            is_patient = obj.profile.role == "patient"
        elif request.POST.get("role") == "patient":
            is_patient = True

        # Exclude license_number for patients
        if is_patient:
            exclude.append("license_number")

        return exclude


class UserAdmin(AdminOnlyMixin, BaseUserAdmin):
    """Custom user admin with profile inline and role-based access - ADMIN ONLY."""

    inlines = (UserProfileInline,)
    add_form = CustomUserCreationForm

    # AC-09.1: list display for admin user management
    list_display = [
        "username",
        "email",
        "get_role",
        "get_department",
        "is_active",
        "date_joined",
    ]
    list_filter = ["is_active", "profile__role", "date_joined"]
    actions = ["deactivate_user"]

    # Simplified add_fieldsets - only User model fields
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
        (
            "Role Assignment",
            {
                "classes": ("wide",),
                "fields": ("role", "department", "license_number", "phone"),
                "description": "Assign role and professional details for the new user.",
            },
        ),
    )

    def get_role(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.get_role_display()
        return "—"

    get_role.short_description = "Role"
    get_role.admin_order_field = "profile__role"

    def get_department(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.department or "—"
        return "—"

    get_department.short_description = "Department"

    def deactivate_user(self, request, queryset):
        """Admin action: set is_active=False for selected users (AC-09.3)."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} user(s) deactivated.")

    deactivate_user.short_description = "Deactivate selected users"

    def has_module_permission(self, request):
        """Allow admin users and superusers to access user management module."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True
        return super().has_module_permission(request)

    def get_form(self, request, obj=None, **kwargs):
        """Use custom form for adding users."""
        if obj is None:  # Adding new user
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        """Use add_fieldsets for new users, regular fieldsets for existing users."""
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def add_view(self, request, form_url="", extra_context=None):
        """Override add view to handle custom form processing."""
        return super().add_view(request, form_url, extra_context)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

    def save_model(self, request, obj, form, change):
        """Atomic role-to-group reassignment on save (AC-09.4)."""
        super().save_model(request, obj, form, change)

        # Ensure profile exists
        if not hasattr(obj, "profile"):
            UserProfile.objects.get_or_create(user=obj, defaults={"role": "patient"})
            return

        # Trigger group re-assignment (handles role changes atomically)
        profile = obj.profile
        profile.assign_to_group()

        # For new users created without the custom add form
        if not change and not hasattr(obj, "profile"):
            UserProfile.objects.get_or_create(user=obj, defaults={"role": "patient"})

    def get_queryset(self, request):
        """Filter users based on role permissions."""
        qs = super().get_queryset(request)

        # Always allow superusers to see all users
        if request.user.is_superuser:
            return qs

        # Allow users with admin role to see all users
        if hasattr(request.user, "profile"):
            if request.user.profile.role == "admin":
                return qs

        # All other users should not access user management at all
        return qs.none()


class UserProfileAdmin(PatientAccessMixin, admin.ModelAdmin):
    """Admin interface for user profiles with role-based filtering."""

    def has_module_permission(self, request):
        """Hide UserProfile admin from patients and nurses (AC-04.2)."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return False

        user_role = request.user.profile.role

        # Patients should not see UserProfile admin - redirect them to Patient admin
        if user_role == "patient":
            return False

        # Nurses should not access UserProfile admin (AC-04.2)
        if user_role == "nurse":
            return False

        # Allow admin, doctor, and pharmacy to access UserProfile admin
        allowed_roles = ["admin", "doctor", "pharmacy"]
        return user_role in allowed_roles

    def has_view_permission(self, request, obj=None):
        """Deny nurse access to UserProfiles (AC-04.2)."""
        if not hasattr(request.user, "profile"):
            return super().has_view_permission(request, obj)
        if request.user.profile.role == "nurse":
            return False
        return super().has_view_permission(request, obj)

    def get_queryset(self, request):
        """Filter profiles based on role permissions."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if hasattr(request.user, "profile"):
            if request.user.profile.role == "admin":
                # Admins can see all profiles
                return qs
            else:
                # All other users can only see their own profile
                return qs.filter(user=request.user)

        return qs.none()

    def get_list_display(self, request):
        """Customize list display based on user role."""
        base_display = ["user", "role"]

        if hasattr(request.user, "profile"):
            user_role = request.user.profile.role

            if user_role == "patient":
                # Patients only see basic info
                return ["user", "role", "phone", "created_at"]
            elif user_role in ["admin"]:
                # Admins see everything
                return [
                    "user",
                    "role",
                    "department",
                    "license_number",
                    "is_complete",
                    "created_at",
                ]
            elif user_role in ["doctor", "nurse", "pharmacy"]:
                # Medical staff see relevant professional info
                return ["user", "role", "department", "license_number", "created_at"]

        # Default view for superusers
        return [
            "user",
            "role",
            "department",
            "license_number",
            "is_complete",
            "created_at",
        ]

    def get_list_filter(self, request):
        """Customize list filters based on user role."""
        if hasattr(request.user, "profile"):
            user_role = request.user.profile.role

            if user_role == "patient":
                # Patients don't need filters since they only see their own profile
                return []
            elif user_role in ["admin"]:
                return ["role", "department", "created_at"]
            else:
                return ["role", "department"]

        return ["role", "department", "created_at"]

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "license_number",
    )
    readonly_fields = ("created_at", "updated_at")

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on user role."""
        base_fieldsets = [
            ("User Information", {"fields": ("user",)}),
            ("Role & Department", {"fields": ("role", "department")}),
        ]

        # Determine if we're dealing with a patient
        is_patient = False
        if obj:
            is_patient = obj.role == "patient"
        elif request.POST.get("role") == "patient":
            is_patient = True

        # Add appropriate contact/professional sections
        if is_patient:
            # Patients only get contact information, no license field
            base_fieldsets.append(("Contact Information", {"fields": ("phone",)}))
        else:
            # Medical staff and others get professional details
            if obj and obj.role in ["doctor", "nurse", "pharmacy"]:
                base_fieldsets.append(
                    ("Professional Details", {"fields": ("license_number", "phone")})
                )
            elif not obj:  # For add form, show all fields with help text
                base_fieldsets.append(
                    (
                        "Professional Details",
                        {
                            "fields": ("license_number", "phone"),
                            "description": "License number required for medical staff (doctors, nurses, pharmacy)",
                        },
                    )
                )
            else:  # For other roles that aren't patients
                base_fieldsets.append(("Contact Information", {"fields": ("phone",)}))

        # Add timestamps
        base_fieldsets.append(
            (
                "Timestamps",
                {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
            )
        )

        return base_fieldsets

    def save_model(self, request, obj, form, change):
        """Override save to ensure validation is enforced."""
        try:
            obj.full_clean()  # This will call the model's clean() method
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            # Add the validation errors to the form
            for field, errors in e.error_dict.items():
                for error in errors:
                    form.add_error(field, error)

    def get_exclude(self, request, obj=None):
        """Exclude fields based on user role."""
        exclude = []

        # Determine if we're dealing with a patient
        is_patient = False
        if obj:
            is_patient = obj.role == "patient"
        elif request.POST.get("role") == "patient":
            is_patient = True

        # Exclude license_number for patients
        if is_patient:
            exclude.append("license_number")

        return exclude

    def get_readonly_fields(self, request, obj=None):
        """Customize readonly fields based on user role."""
        readonly_fields = list(self.readonly_fields)

        if not request.user.is_superuser and hasattr(request.user, "profile"):
            user_role = request.user.profile.role

            # Patients and non-admin users can't change certain fields
            if user_role == "patient":
                readonly_fields.extend(["user", "role", "department"])
                # Patients shouldn't see license_number field at all
                if obj and obj.role != "patient":
                    readonly_fields.append("license_number")
            elif user_role != "admin":
                readonly_fields.append("role")

        return readonly_fields

    def filter_queryset_by_role(self, request, queryset, role):
        """Apply role-specific filtering."""
        if role == "admin":
            # Admins can see all profiles
            return queryset
        else:
            # All other users can only see their own profile
            return queryset.filter(user=request.user)

    def has_add_permission(self, request):
        """Only admins and superusers can add user profiles directly."""
        if not super().has_add_permission(request):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile"):
            return request.user.profile.role == "admin"
        return False

    def has_delete_permission(self, request, obj=None):
        """Only admins and superusers can delete profiles."""
        if not super().has_delete_permission(request, obj):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile"):
            return request.user.profile.role == "admin"
        return False

    def is_complete(self, obj):
        """Display profile completion status."""
        return obj.is_complete

    is_complete.boolean = True
    is_complete.short_description = "Profile Complete"

    actions = ["sync_user_groups"]

    def sync_user_groups(self, request, queryset):
        """Sync every UserProfile to the Group matching its role field (AC-11.3)."""
        count = 0
        for profile in queryset:
            profile.assign_to_group()
            count += 1
        self.message_user(request, f"Synced {count} user profile(s) to correct groups.")

    sync_user_groups.short_description = "Sync user groups to match role"


class EmergencyContactInline(admin.StackedInline):
    """Inline admin for emergency contacts."""

    model = EmergencyContact
    extra = 1
    max_num = 5
    fields = [
        "name",
        "relationship",
        "phone_primary",
        "phone_secondary",
        "email",
        "is_primary_contact",
        "notes",
    ]

    def get_readonly_fields(self, request, obj=None):
        """Read-only for nurses (AC-01.4) and patients viewing others' records."""
        if hasattr(request.user, "profile"):
            role = request.user.profile.role
            # Nurses have read-only access to emergency contacts (AC-03.1)
            if role == "nurse":
                return list(self.fields)
            if role == "patient":
                if obj and obj.user_profile != request.user.profile:
                    # Patient trying to view another patient's data
                    return list(self.fields)
        return []


class MedicationInline(admin.TabularInline):
    """
    Inline for patient medications (PMS-014).

    - Admin / superuser : full add / edit / delete
    - Doctor            : add / edit for assigned patients;
                          prescribing_doctor auto-set via PatientAdmin.save_formset
    - Nurse / Pharmacy  : read-only view (FR-N-2 / FR-Ph-1)
    - Patient           : not shown (excluded by PatientAdmin.get_inlines)
    """

    model = Medication
    extra = 0
    fields = [
        "medication_name",
        "dosage",
        "frequency",
        "prescribing_doctor",
        "start_date",
        "end_date",
        "status",
        "notes",
    ]

    def get_readonly_fields(self, request, obj=None):
        if hasattr(request.user, "profile"):
            if request.user.profile.role in ["nurse", "pharmacy"]:
                return list(self.fields)
        return []

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile"):
            return request.user.profile.role in ["admin", "doctor"]
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile"):
            return request.user.profile.role in ["admin", "doctor"]
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile"):
            return request.user.profile.role == "admin"
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "prescribing_doctor":
            kwargs["queryset"] = UserProfile.objects.filter(role="doctor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Patient)
class PatientAdmin(PatientAccessMixin, admin.ModelAdmin):
    """Admin interface for patient records with role-based access."""

    form = PatientAdminForm
    list_display = [
        "medical_id",
        "get_patient_name",
        "get_assigned_doctor",
        "age",
        "gender",
        "phone_primary",
        "city",
        "state",
        "created_at",
    ]
    list_filter = [
        "gender",
        "blood_type",
        "state",
        "assigned_doctor",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "medical_id",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "user_profile__user__username",
        "assigned_doctor__user__first_name",
        "assigned_doctor__user__last_name",
        "phone_primary",
        "city",
        "insurance_number",
    ]
    readonly_fields = ["medical_id", "age", "created_at", "updated_at"]

    fieldsets = (
        (
            "Patient Identity",
            {
                "fields": ("user_profile", "medical_id"),
                "description": "Your unique patient identification information",
            },
        ),
        (
            "Care Assignment",
            {
                "fields": ("assigned_doctor", "assigned_nurse"),
                "description": (
                    "Doctor and nurse assigned to this patient " "(admin-only)"
                ),
            },
        ),
        (
            "Personal Information",
            {
                "fields": ("date_of_birth", "gender", "blood_type", "insurance_number"),
                "description": "Please ensure your personal details are accurate",
            },
        ),
        (
            "Contact Information",
            {
                "fields": ("phone_primary", "phone_secondary", "email_personal"),
                "description": "How we can reach you in case of emergencies or appointments",
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                ),
                "description": "Your current residential address",
            },
        ),
        (
            "Medical History",
            {
                "fields": (
                    "diagnoses",
                    "procedures",
                    "visit_notes",
                    "allergies",
                    "chronic_conditions",
                ),
                "description": (
                    "Clinical diagnoses, procedures, prior visit notes, "
                    "allergies and chronic conditions \u2014 FR-D-4"
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [EmergencyContactInline]

    def get_inlines(self, request, obj=None):
        """Show MedicationInline for clinical staff; hide it for patients."""
        role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )
        if request.user.is_superuser or role in [
            "admin",
            "doctor",
            "nurse",
            "pharmacy",
        ]:
            return [EmergencyContactInline, MedicationInline]
        # patient role — emergency contacts only
        return [EmergencyContactInline]

    # WF-S3-01: hint text shown below the search box in the changelist
    search_help_text = (
        "Search by first name, last name, medical ID, or assigned doctor name — FR-D-6"
    )

    # Enable date drill-down in changelist for admin/superuser
    date_hierarchy = "created_at"

    def get_search_fields(self, request):
        """
        Return role-appropriate search fields (FR-D-6).

        - patient   : no search (only their own record is shown)
        - doctor    : name + medical ID over their assigned patients (FR-D-6)
        - nurse /
          pharmacy  : name, medical ID, phone, city across all patients
        - admin /
          superuser : full field set (includes assigned-doctor name, insurance,
                      phone, city, etc.)
        """
        user_role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

        if user_role == "patient":
            # Patient sees only their own record — search is irrelevant
            return []

        if user_role == "doctor":
            # FR-D-6: doctors search by name or medical ID within their own patients
            return [
                "medical_id",
                "user_profile__user__first_name",
                "user_profile__user__last_name",
                "user_profile__user__username",
            ]

        if user_role in ["nurse", "pharmacy"]:
            # Nurses / pharmacy: name, ID, phone and city
            return [
                "medical_id",
                "user_profile__user__first_name",
                "user_profile__user__last_name",
                "user_profile__user__username",
                "phone_primary",
                "city",
            ]

        # Admin and superuser: full search capability
        return list(self.search_fields)

    def get_patient_name(self, obj):
        """Display patient's full name."""
        return obj.user_profile.user.get_full_name() or obj.user_profile.user.username

    get_patient_name.short_description = "Patient Name"
    get_patient_name.admin_order_field = "user_profile__user__last_name"

    def get_assigned_doctor(self, obj):
        """Display assigned doctor's name."""
        if obj.assigned_doctor:
            return (
                obj.assigned_doctor.user.get_full_name()
                or obj.assigned_doctor.user.username
            )
        return "Unassigned"

    get_assigned_doctor.short_description = "Assigned Doctor"
    get_assigned_doctor.admin_order_field = "assigned_doctor__user__last_name"

    def get_assigned_nurse(self, obj):
        """Display assigned nurse's name."""
        if obj.assigned_nurse:
            return (
                obj.assigned_nurse.user.get_full_name()
                or obj.assigned_nurse.user.username
            )
        return "Unassigned"

    get_assigned_nurse.short_description = "Assigned Nurse"
    get_assigned_nurse.admin_order_field = "assigned_nurse__user__last_name"

    def get_chronic_conditions_short(self, obj):
        """Truncated chronic conditions for nurse list display (AC-01.2)."""
        if obj.chronic_conditions:
            text = obj.chronic_conditions
            return text[:80] + ("\u2026" if len(text) > 80 else "")
        return "\u2014"

    get_chronic_conditions_short.short_description = "Chronic Conditions"
    get_chronic_conditions_short.admin_order_field = "chronic_conditions"

    def get_diagnoses_short(self, obj):
        """Truncated diagnosis summary for doctor list display (AC-05.2)."""
        if obj.diagnoses:
            text = obj.diagnoses
            return text[:60] + ("\u2026" if len(text) > 60 else "")
        return "\u2014"

    get_diagnoses_short.short_description = "Diagnosis Summary"

    def get_pending_test_count(self, obj):
        """Count of pending test results for this patient (AC-05.2)."""
        return obj.test_results.filter(status="pending").count()

    get_pending_test_count.short_description = "Pending Tests"

    def get_next_appointment(self, obj):
        """Next upcoming appointment date for this patient (AC-05.2)."""
        now = timezone.now()
        appt = (
            obj.appointments.filter(appointment_datetime__gte=now)
            .exclude(status__in=["completed", "cancelled"])
            .order_by("appointment_datetime")
            .first()
        )
        if appt:
            return appt.appointment_datetime.strftime("%Y-%m-%d %H:%M")
        return "\u2014"

    get_next_appointment.short_description = "Next Appointment"

    def age(self, obj):
        """Display patient's age."""
        return obj.age

    age.short_description = "Age"

    def get_list_display(self, request):
        """Return role-specific list display columns."""
        user_role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

        if user_role == "patient":
            # Patients see a simplified view of their own record
            return ["medical_id", "get_patient_name", "age", "gender", "phone_primary"]

        if user_role == "doctor":
            # AC-05.2: name, medical ID, DOB, diagnosis summary, pending tests, next appt
            return [
                "medical_id",
                "get_patient_name",
                "date_of_birth",
                "get_diagnoses_short",
                "get_pending_test_count",
                "get_next_appointment",
            ]

        if user_role == "nurse":
            # AC-01.2: nurses see name, DOB, blood type, assigned doctor, chronic conditions
            return [
                "get_patient_name",
                "date_of_birth",
                "blood_type",
                "get_assigned_doctor",
                "get_chronic_conditions_short",
            ]

        if user_role == "pharmacy":
            # Pharmacy focuses on identification and contact
            return [
                "medical_id",
                "get_patient_name",
                "get_assigned_doctor",
                "age",
                "gender",
                "phone_primary",
                "city",
            ]

        # Admin and superuser — full list
        return [
            "medical_id",
            "get_patient_name",
            "get_assigned_doctor",
            "get_assigned_nurse",
            "age",
            "gender",
            "phone_primary",
            "city",
            "state",
            "created_at",
        ]

    def get_list_filter(self, request):
        """Return role-specific list filters."""
        user_role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

        if user_role == "patient":
            # Patients only see their own record — filters add no value
            return []

        if user_role == "doctor":
            # WF-S3-01: filters hidden for Doctor view — they only see their
            # own patients already, so additional filtering adds little value
            return []

        if user_role == "nurse":
            # Nurses see only their assigned patients — no extra filter needed
            return []

        if user_role == "pharmacy":
            # Pharmacy sees all patients — basic clinical filter
            return ["gender", "blood_type", "state", CityListFilter]

        # Admin and superuser — full filter set
        return [
            "gender",
            "blood_type",
            "state",
            "assigned_doctor",
            "assigned_nurse",
            CityListFilter,
            "created_at",
            "updated_at",
        ]

    def get_queryset(self, request):
        """Filter patients based on user role."""
        qs = super().get_queryset(request)

        # Superusers see everything
        if request.user.is_superuser:
            return qs

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return qs.none()

        user_role = request.user.profile.role

        # Role-based filtering
        if user_role == "admin":
            # Admins can see all patients
            return qs
        elif user_role == "patient":
            # Auto-create Patient record if it doesn't exist
            request.user.profile.ensure_patient_record()
            # Patients can only see their own record
            return qs.filter(user_profile=request.user.profile)
        elif user_role == "doctor":
            # Doctors can only see patients assigned to them
            return qs.filter(assigned_doctor=request.user.profile)
        elif user_role == "nurse":
            # FR-N-1: nurses see only their assigned patients
            return qs.filter(assigned_nurse=request.user.profile)
        elif user_role == "pharmacy":
            # Pharmacy staff can see all patients
            return qs
        else:
            # Other roles see nothing
            return qs.none()

    def get_readonly_fields(self, request, obj=None):
        """Set readonly fields based on user role.

        Editable fields per role:
          admin/superuser — everything except auto-generated fields
          patient         — insurance_number, phone_primary, phone_secondary,
                            email_personal, all address fields
          doctor          — personal info, contact, address
                            (identity & care assignment are readonly)
          nurse/pharmacy  — contact info (phone, email) and address only
        """
        # Base readonly fields are always locked (auto-generated / timestamps)
        readonly_fields = list(
            self.readonly_fields
        )  # medical_id, age, created_at, updated_at

        user_role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

        if user_role == "patient":
            if obj and obj.user_profile != request.user.profile:
                # Patient attempting to view another patient's record — lock everything
                return [field.name for field in self.model._meta.fields]
            # Patient editing their own record:
            # editable: insurance_number, phone_primary, phone_secondary,
            #           email_personal, and all address fields
            readonly_fields.extend(
                [
                    "user_profile",
                    "assigned_doctor",
                    "assigned_nurse",
                    "date_of_birth",
                    "gender",
                    "blood_type",
                ]
            )

        elif user_role == "doctor":
            # Doctors can update personal info, contact and address
            # but cannot alter patient identity or care assignment
            readonly_fields.extend(
                [
                    "user_profile",
                    "assigned_doctor",
                    "assigned_nurse",
                ]
            )

        elif user_role in ["nurse", "pharmacy"]:
            # All fields readonly for nurse (AC-01.4); clinical fields readonly for pharmacy
            readonly_fields.extend(
                [
                    "user_profile",
                    "assigned_doctor",
                    "assigned_nurse",
                    "date_of_birth",
                    "gender",
                    "blood_type",
                    "insurance_number",
                    # Contact information — readonly for nurse (AC-01.4)
                    "phone_primary",
                    "phone_secondary",
                    "email_personal",
                    # Address — readonly for nurse
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                    # Medical History — always readonly for nurse/pharmacy
                    "diagnoses",
                    "procedures",
                    "visit_notes",
                    "allergies",
                    "chronic_conditions",
                ]
            )

        # Admin and superuser: only the base readonly_fields apply
        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        """Return role-specific fieldsets to control field visibility per role."""
        user_role = (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

        # ── Admin / superuser ── full view of all fields
        if request.user.is_superuser or user_role == "admin":
            return self.fieldsets

        # ── Patient ── own record only; no user_profile, no care assignment exposed
        if user_role == "patient":
            return (
                (
                    "Patient Identity",
                    {
                        "fields": ("medical_id",),
                        "description": "Your unique patient identification information",
                    },
                ),
                (
                    "Personal Information",
                    {
                        "fields": (
                            "date_of_birth",
                            "gender",
                            "blood_type",
                            "insurance_number",
                        ),
                        "description": "Please ensure your personal details are accurate",
                    },
                ),
                (
                    "Contact Information",
                    {
                        "fields": (
                            "phone_primary",
                            "phone_secondary",
                            "email_personal",
                        ),
                        "description": "How we can reach you in case of emergencies or appointments",
                    },
                ),
                (
                    "Address",
                    {
                        "fields": (
                            "address_line1",
                            "address_line2",
                            "city",
                            "state",
                            "postal_code",
                            "country",
                        ),
                        "description": "Your current residential address",
                    },
                ),
            )

        # ── Doctor ── assigned patients; care assignment shown but readonly
        if user_role == "doctor":
            return (
                (
                    "Patient Identity",
                    {
                        "fields": ("user_profile", "medical_id"),
                        "description": "Patient identification information",
                    },
                ),
                (
                    "Care Assignment",
                    {
                        "fields": (
                            "assigned_doctor",
                            "assigned_nurse",
                        ),
                        "description": (
                            "Assigned care providers " "(read-only for doctors)"
                        ),
                    },
                ),
                (
                    "Personal Information",
                    {
                        "fields": (
                            "date_of_birth",
                            "gender",
                            "blood_type",
                            "insurance_number",
                        ),
                    },
                ),
                (
                    "Contact Information",
                    {
                        "fields": (
                            "phone_primary",
                            "phone_secondary",
                            "email_personal",
                        ),
                    },
                ),
                (
                    "Address",
                    {
                        "fields": (
                            "address_line1",
                            "address_line2",
                            "city",
                            "state",
                            "postal_code",
                            "country",
                        ),
                    },
                ),
                (
                    "Medical History",
                    {
                        "fields": (
                            "diagnoses",
                            "procedures",
                            "visit_notes",
                            "allergies",
                            "chronic_conditions",
                        ),
                        "description": (
                            "Clinical diagnoses, procedures and prior "
                            "visit notes \u2014 FR-D-4"
                        ),
                        "classes": ("collapse",),
                    },
                ),
                (
                    "System Information",
                    {
                        "fields": ("created_at", "updated_at"),
                        "classes": ("collapse",),
                    },
                ),
            )

        # ── Nurse ── read-only clinical view + medical history (FR-N-2)
        if user_role == "nurse":
            return (
                (
                    "Patient Identity",
                    {
                        "fields": ("user_profile", "medical_id"),
                        "description": "Patient identification information",
                    },
                ),
                (
                    "Care Assignment",
                    {
                        "fields": (
                            "assigned_doctor",
                            "assigned_nurse",
                        ),
                        "description": ("Assigned care providers (read-only)"),
                    },
                ),
                (
                    "Personal Information",
                    {
                        "fields": ("date_of_birth", "gender", "blood_type"),
                    },
                ),
                (
                    "Contact Information",
                    {
                        "fields": (
                            "phone_primary",
                            "phone_secondary",
                            "email_personal",
                        ),
                    },
                ),
                (
                    "Address",
                    {
                        "fields": (
                            "address_line1",
                            "address_line2",
                            "city",
                            "state",
                            "postal_code",
                            "country",
                        ),
                    },
                ),
                (
                    "Medical History",
                    {
                        "fields": (
                            "diagnoses",
                            "procedures",
                            "visit_notes",
                            "allergies",
                            "chronic_conditions",
                        ),
                        "description": (
                            "Clinical history \u2014 read-only for nurses " "(FR-N-2)"
                        ),
                        "classes": ("collapse",),
                    },
                ),
            )

        # ── Pharmacy ── allergy info only (FR-Ph-3)
        if user_role == "pharmacy":
            return (
                (
                    "Patient Identity",
                    {
                        "fields": ("user_profile", "medical_id"),
                        "description": "Patient identification information",
                    },
                ),
                (
                    "Care Assignment",
                    {
                        "fields": ("assigned_doctor",),
                        "description": "Assigned care provider (read-only)",
                    },
                ),
                (
                    "Personal Information",
                    {
                        "fields": ("date_of_birth", "gender", "blood_type"),
                    },
                ),
                (
                    "Contact Information",
                    {
                        "fields": (
                            "phone_primary",
                            "phone_secondary",
                            "email_personal",
                        ),
                    },
                ),
                (
                    "Address",
                    {
                        "fields": (
                            "address_line1",
                            "address_line2",
                            "city",
                            "state",
                            "postal_code",
                            "country",
                        ),
                    },
                ),
                (
                    "Allergy Information",
                    {
                        "fields": ("allergies",),
                        "description": (
                            "Patient allergy information \u2014 " "FR-Ph-3 (read-only)"
                        ),
                    },
                ),
            )

        # Fallback — full fieldsets
        return self.fieldsets

    def save_formset(self, request, form, formset, change):
        """Auto-set prescribing_doctor when a doctor adds a medication."""
        if formset.model is Medication:
            instances = formset.save(commit=False)
            for obj in instances:
                if (
                    not obj.prescribing_doctor
                    and hasattr(request.user, "profile")
                    and request.user.profile.role == "doctor"
                ):
                    obj.prescribing_doctor = request.user.profile
                obj.save()
            formset.save_m2m()
            for obj in formset.deleted_objects:
                obj.delete()
        else:
            super().save_formset(request, form, formset, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict FK dropdowns to appropriate roles."""
        if db_field.name == "assigned_doctor":
            kwargs["queryset"] = UserProfile.objects.filter(role="doctor")
        if db_field.name == "assigned_nurse":
            kwargs["queryset"] = UserProfile.objects.filter(role="nurse")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        """Only admins and superusers can create new patient records."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True
        return False

    def has_change_permission(self, request, obj=None):
        """Control who can change patient records."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return False

        user_role = request.user.profile.role

        if user_role == "admin":
            return True

        if user_role == "doctor":
            if obj is None:  # Changelist view — allow to see the list
                return True
            # Object-level: only assigned patients
            return obj.assigned_doctor == request.user.profile

        # Nurses and pharmacy are read-only via has_view_permission
        if user_role in ["nurse", "pharmacy"]:
            return False

        # Allow patients to change their own records
        if user_role == "patient":
            if obj is None:  # For changelist view
                return True
            else:  # For specific object
                return obj.user_profile == request.user.profile

        return False

    def has_delete_permission(self, request, obj=None):
        """Only admins and superusers can delete patient records."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True
        return False

    def has_view_permission(self, request, obj=None):
        """Allow patients to view their own records."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return False

        user_role = request.user.profile.role

        # Allow admin and medical staff full access
        if user_role in ["admin", "doctor", "pharmacy"]:
            return True

        # Nurse: object-level check — only view assigned patients (AC-01.3)
        if user_role == "nurse":
            if obj is None:  # Changelist view is allowed
                return True
            return obj.assigned_nurse == request.user.profile

        # Allow patients to view their own records
        if user_role == "patient":
            if obj is None:  # For changelist view
                return True
            else:  # For specific object
                return obj.user_profile == request.user.profile

        return False

    def has_module_permission(self, request):
        """Allow patients to access the Patient admin module."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return False

        user_role = request.user.profile.role

        # Allow admin, medical staff, and patients to access Patient admin
        allowed_roles = ["admin", "doctor", "nurse", "pharmacy", "patient"]
        return user_role in allowed_roles

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to provide helpful context for patients."""
        extra_context = extra_context or {}

        # Add helpful message for patient users
        if hasattr(request.user, "profile") and request.user.profile.role == "patient":
            extra_context["patient_help_message"] = (
                "Welcome! Below you can view and update your patient information. "
                "Please make sure all your details are accurate and up-to-date."
            )
            request.user.profile.ensure_patient_record()

        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Override change view: audit log read + helpful context for patients (AC-14.1)."""
        extra_context = extra_context or {}

        # Write audit log READ entry (AC-14.1)
        try:
            obj = self.get_object(request, object_id)
            if obj is not None:
                _write_audit_log(request, "read", obj)
        except Exception:
            pass

        if hasattr(request.user, "profile") and request.user.profile.role == "patient":
            extra_context["patient_help_message"] = (
                "Please update your information below. Fields marked with placeholder text "
                "should be updated with your actual information."
            )

        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        """Audit-log create/update events (AC-15.1 / AC-15.2)."""
        if change and obj.pk:
            # Capture old values before save
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_data = _snapshot(old_obj)
            except self.model.DoesNotExist:
                old_data = {}
            super().save_model(request, obj, form, change)
            new_data = _snapshot(obj)
            _write_audit_log(
                request, "update", obj, _build_changes_summary(old_data, new_data)
            )
        else:
            super().save_model(request, obj, form, change)
            _write_audit_log(request, "create", obj)

    def delete_model(self, request, obj):
        """Audit-log delete events (AC-15.3)."""
        _write_audit_log(request, "delete", obj)
        super().delete_model(request, obj)


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    """Admin interface for emergency contacts."""

    list_display = [
        "name",
        "patient",
        "relationship",
        "phone_primary",
        "is_primary_contact",
    ]
    list_filter = ["relationship", "is_primary_contact", "created_at"]
    search_fields = [
        "name",
        "patient__medical_id",
        "patient__user_profile__user__first_name",
        "patient__user_profile__user__last_name",
    ]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Contact Information", {"fields": ("patient", "name", "relationship")}),
        ("Phone & Email", {"fields": ("phone_primary", "phone_secondary", "email")}),
        ("Status & Notes", {"fields": ("is_primary_contact", "notes")}),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        """Filter emergency contacts based on user role."""
        qs = super().get_queryset(request)

        # Superusers see everything
        if request.user.is_superuser:
            return qs

        # Check if user has a profile
        if not hasattr(request.user, "profile"):
            return qs.none()

        user_role = request.user.profile.role

        # Role-based filtering
        if user_role == "admin":
            # Admins can see all emergency contacts
            return qs
        elif user_role == "patient":
            # Patients can only see their own emergency contacts
            return qs.filter(patient__user_profile=request.user.profile)
        elif user_role == "nurse":
            # Task 4 (AC-03.1): nurses see only contacts for their assigned patients
            return qs.filter(patient__assigned_nurse=request.user.profile)
        elif user_role in ["doctor", "pharmacy"]:
            # Doctors and pharmacy can see all emergency contacts
            return qs
        else:
            # Other roles see nothing
            return qs.none()

    def has_module_permission(self, request):
        """Allow nurses and other medical staff to access emergency contacts."""
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in [
            "admin",
            "doctor",
            "nurse",
            "pharmacy",
            "patient",
        ]

    def has_view_permission(self, request, obj=None):
        """Object-level read access; nurses restricted to assigned patients (AC-03.1)."""
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role == "admin":
            return True
        if role in ["doctor", "pharmacy"]:
            return True
        if role == "nurse":
            if obj is None:
                return True
            return obj.patient.assigned_nurse == request.user.profile
        if role == "patient":
            if obj is None:
                return True
            return obj.patient.user_profile == request.user.profile
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor"]

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor"]

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role == "admin"


class TestResultAdminForm(forms.ModelForm):
    """Custom form: limits ordering_doctor choices to doctors only."""

    class Meta:
        model = TestResult
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "ordering_doctor" in self.fields:
            self.fields["ordering_doctor"].queryset = UserProfile.objects.filter(
                role="doctor"
            )
            self.fields["ordering_doctor"].required = False


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    """
    Admin interface for lab / clinical test results (PMS-013).

    Role access — WF-S4-01, WF-S4-02:
      admin / superuser — full CRUD, all patients
      doctor            — add/edit results for assigned patients;
                          ordering_doctor auto-set on save
      nurse             — read-only list, all patients
      patient           — read-only list, own results only (FR-P-1)
      pharmacy          — no access
    """

    form = TestResultAdminForm

    list_display = [
        "test_date",
        "test_name",
        "get_patient_display",
        "get_ordering_doctor_display",
        "get_result_display",
        "reference_range",
        "status",
        "follow_up_required",
    ]
    list_filter = ["test_type", "status", "ordering_doctor"]
    search_fields = [
        "test_name",
        "patient__medical_id",
        "patient__user_profile__user__first_name",
        "patient__user_profile__user__last_name",
        "ordering_doctor__user__first_name",
        "ordering_doctor__user__last_name",
    ]
    search_help_text = (
        "Search by test name, patient name / medical ID, " "or ordering doctor name"
    )
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "test_date"
    ordering = ["-test_date", "-created_at"]

    fieldsets = (
        (
            "Patient Information",
            {
                "fields": ("patient", "ordering_doctor"),
                "description": "Patient and doctor who ordered this test",
            },
        ),
        (
            "Test Information",
            {
                "fields": (
                    "test_name",
                    "test_type",
                    "test_date",
                    "result_value",
                    "result_unit",
                    "reference_range",
                    "status",
                ),
                "description": "Test details and results \u2014 FR-P-2",
            },
        ),
        (
            "Doctor Notes",
            {
                "fields": ("doctor_notes", "follow_up_required"),
                "description": ("Clinical notes and follow-up requirements"),
            },
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # ── display helpers ───────────────────────────────────────────────

    def get_patient_display(self, obj):
        """Full patient name and medical ID."""
        return str(obj.patient)

    get_patient_display.short_description = "Patient"
    get_patient_display.admin_order_field = "patient__user_profile__user__last_name"

    def get_ordering_doctor_display(self, obj):
        """Ordering doctor full name."""
        if obj.ordering_doctor:
            return (
                obj.ordering_doctor.user.get_full_name()
                or obj.ordering_doctor.user.username
            )
        return "\u2014"

    get_ordering_doctor_display.short_description = "Ordering Doctor"
    get_ordering_doctor_display.admin_order_field = "ordering_doctor__user__last_name"

    def get_result_display(self, obj):
        """Result value with unit appended when present."""
        if obj.result_unit:
            return f"{obj.result_value} {obj.result_unit}"
        return obj.result_value

    get_result_display.short_description = "Result"
    get_result_display.admin_order_field = "result_value"

    def critical_status_badge(self, obj):
        """Render a bold red badge for critical-status rows (AC-06.3)."""
        if obj.status == "critical":
            return format_html('<strong style="color:red;">&#9888; CRITICAL</strong>')
        return obj.get_status_display()

    critical_status_badge.short_description = "Status"
    critical_status_badge.admin_order_field = "status"

    # ── role helper ───────────────────────────────────────────────────

    def _user_role(self, request):
        """Return the requesting user's role string, or None."""
        return (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

    # ── role-aware overrides ──────────────────────────────────────────

    def get_list_display(self, request):
        role = self._user_role(request)
        if role == "patient":
            # FR-P-2: show name, date, value, reference range, status
            return [
                "test_date",
                "test_name",
                "get_result_display",
                "reference_range",
                "critical_status_badge",
                "doctor_notes",
            ]
        if role == "doctor":
            # AC-06.3: show critical badge + ordering by test_date desc
            return [
                "test_date",
                "test_name",
                "get_patient_display",
                "get_result_display",
                "reference_range",
                "critical_status_badge",
                "follow_up_required",
            ]
        if role == "nurse":
            return [
                "test_date",
                "test_name",
                "get_patient_display",
                "get_ordering_doctor_display",
                "get_result_display",
                "reference_range",
                "status",
            ]
        # Admin / superuser
        return list(self.list_display)

    def get_list_filter(self, request):
        role = self._user_role(request)
        if role == "patient":
            return ["status", "test_type"]
        if role == "doctor":
            return ["test_type", "status"]
        # Admin, superuser, nurse
        return ["test_type", "status", "ordering_doctor"]

    def get_search_fields(self, request):
        role = self._user_role(request)
        if role == "patient":
            return ["test_name"]
        if role == "doctor":
            return [
                "test_name",
                "patient__medical_id",
                "patient__user_profile__user__first_name",
                "patient__user_profile__user__last_name",
            ]
        return list(self.search_fields)

    def get_readonly_fields(self, request, obj=None):
        role = self._user_role(request)
        if role in ["patient", "nurse"]:
            # All fields read-only for patients and nurses
            all_field_names = [
                f.name for f in TestResult._meta.get_fields() if hasattr(f, "column")
            ]
            return list(set(all_field_names + ["created_at", "updated_at"]))
        if role == "doctor":
            # ordering_doctor auto-set; keep read-only in the form
            return list(self.readonly_fields) + ["ordering_doctor"]
        return list(self.readonly_fields)

    def get_fieldsets(self, request, obj=None):
        role = self._user_role(request)

        if role == "patient":
            # FR-P-2: result details + notes; hide patient FK
            return (
                (
                    "Test Information",
                    {
                        "fields": (
                            "test_name",
                            "test_type",
                            "test_date",
                            "result_value",
                            "result_unit",
                            "reference_range",
                            "status",
                        ),
                        "description": ("Your laboratory test results \u2014 FR-P-2"),
                    },
                ),
                (
                    "Doctor Notes",
                    {
                        "fields": (
                            "doctor_notes",
                            "follow_up_required",
                        ),
                    },
                ),
            )

        if role == "nurse":
            return (
                (
                    "Patient Information",
                    {"fields": ("patient", "ordering_doctor")},
                ),
                (
                    "Test Information",
                    {
                        "fields": (
                            "test_name",
                            "test_type",
                            "test_date",
                            "result_value",
                            "result_unit",
                            "reference_range",
                            "status",
                        ),
                    },
                ),
            )

        if role == "doctor":
            return (
                (
                    "Patient Information",
                    {
                        "fields": ("patient", "ordering_doctor"),
                        "description": (
                            "Patient filtered to your assigned patients. "
                            "Ordering doctor is set automatically."
                        ),
                    },
                ),
                (
                    "Test Information",
                    {
                        "fields": (
                            "test_name",
                            "test_type",
                            "test_date",
                            "result_value",
                            "result_unit",
                            "reference_range",
                            "status",
                        ),
                    },
                ),
                (
                    "Doctor Notes",
                    {
                        "fields": (
                            "doctor_notes",
                            "follow_up_required",
                        ),
                    },
                ),
            )

        # Admin / superuser — full fieldsets
        return self.fieldsets

    # ── queryset ──────────────────────────────────────────────────────

    def get_queryset(self, request):
        """Role-scoped test results \u2014 FR-D-1, FR-P-1, FR-AA-2."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, "profile"):
            return qs.none()

        role = request.user.profile.role

        if role == "admin":
            return qs
        if role == "doctor":
            # FR-D-1: results for assigned patients OR tests the doctor ordered.
            # A doctor may be the ordering_doctor even if the patient has since
            # been reassigned — both cases must be visible.
            return qs.filter(
                Q(patient__assigned_doctor=request.user.profile)
                | Q(ordering_doctor=request.user.profile)
            ).distinct()
        if role == "patient":
            # FR-P-1 / FR-P-3: only own results
            return qs.filter(patient__user_profile=request.user.profile)
        if role == "nurse":
            # FR-N-1: nurse sees results for their assigned patients only
            return qs.filter(patient__assigned_nurse=request.user.profile)
        return qs.none()

    # ── permissions ───────────────────────────────────────────────────

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor", "nurse", "patient"]

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor"]

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role == "admin":
            return True
        if role == "doctor":
            if obj is None:
                return True
            # Doctor may only edit results for their own patients
            return obj.patient.assigned_doctor == request.user.profile
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role == "admin"

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role in ["admin", "doctor", "nurse"]:
            return True
        if role == "patient":
            if obj is None:
                return True
            return obj.patient.user_profile == request.user.profile
        return False

    # ── FK filtering and auto-set ─────────────────────────────────────

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter patient dropdown for doctors; restrict doctor field."""
        if db_field.name == "patient":
            if (
                not request.user.is_superuser
                and hasattr(request.user, "profile")
                and request.user.profile.role == "doctor"
            ):
                kwargs["queryset"] = Patient.objects.filter(
                    assigned_doctor=request.user.profile
                )
        if db_field.name == "ordering_doctor":
            kwargs["queryset"] = UserProfile.objects.filter(role="doctor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-assign ordering_doctor; audit-log create/update (AC-06.4, AC-15.1/15.2)."""
        if (
            not obj.ordering_doctor
            and hasattr(request.user, "profile")
            and request.user.profile.role == "doctor"
        ):
            obj.ordering_doctor = request.user.profile
        if change and obj.pk:
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_data = _snapshot(old_obj)
            except self.model.DoesNotExist:
                old_data = {}
            super().save_model(request, obj, form, change)
            _write_audit_log(
                request, "update", obj, _build_changes_summary(old_data, _snapshot(obj))
            )
        else:
            super().save_model(request, obj, form, change)
            _write_audit_log(request, "create", obj)

    def delete_model(self, request, obj):
        """Audit-log delete (AC-15.3)."""
        _write_audit_log(request, "delete", obj)
        super().delete_model(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Audit-log read (AC-14.2)."""
        extra_context = extra_context or {}
        try:
            obj = self.get_object(request, object_id)
            if obj is not None:
                _write_audit_log(request, "read", obj)
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


# ── Medication Admin ──────────────────────────────────────────────────────


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    """Admin view for Medication records — FR-D-4 / FR-N-2 / FR-Ph-1."""

    list_display = [
        "medication_name",
        "dosage",
        "frequency",
        "get_patient_display",
        "get_doctor_display",
        "start_date",
        "end_date",
        "status",
        "fulfillment_status",
        "allergy_conflict_warning",
    ]
    list_filter = ["status", "fulfillment_status", "prescribing_doctor"]
    search_fields = [
        "medication_name",
        "patient__medical_id",
        "patient__user_profile__user__first_name",
        "patient__user_profile__user__last_name",
        "prescribing_doctor__user__first_name",
        "prescribing_doctor__user__last_name",
    ]
    ordering = ["status", "-start_date"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "patient",
                    "medication_name",
                    "dosage",
                    "frequency",
                    "prescribing_doctor",
                    "start_date",
                    "end_date",
                    "status",
                    "fulfillment_status",
                    "notes",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # ── Display helpers ──────────────────────────────────────────────

    def get_patient_display(self, obj):
        """Full name + medical ID."""
        name = (
            obj.patient.user_profile.user.get_full_name()
            or obj.patient.user_profile.user.username
        )
        return f"{name} ({obj.patient.medical_id})"

    get_patient_display.short_description = "Patient"
    get_patient_display.admin_order_field = "patient__user_profile__user__last_name"

    def get_doctor_display(self, obj):
        """Prescribing doctor full name."""
        if obj.prescribing_doctor:
            return (
                obj.prescribing_doctor.user.get_full_name()
                or obj.prescribing_doctor.user.username
            )
        return "—"

    get_doctor_display.short_description = "Prescribing Doctor"
    get_doctor_display.admin_order_field = "prescribing_doctor__user__last_name"

    def allergy_conflict_warning(self, obj):
        """Display a warning indicator when allergy_conflict is True (FR-Ph-5 / AC-05.1)."""
        if obj.allergy_conflict:
            return format_html(
                '<span style="color:red; font-weight:bold;">&#9888; Allergy conflict detected</span>'
            )
        return ""

    allergy_conflict_warning.short_description = "Allergy Conflict"
    allergy_conflict_warning.admin_order_field = "allergy_conflict"

    # ── Role-aware list overrides ─────────────────────────────────────

    def _med_role(self, request):
        return (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

    def get_list_display(self, request):
        """Nurse sees a focused medication list with allergy indicator (AC-02.2)."""
        if self._med_role(request) == "nurse":
            return [
                "get_patient_display",
                "medication_name",
                "dosage",
                "frequency",
                "start_date",
                "status",
                "allergy_conflict_warning",
            ]
        return list(self.list_display)

    def get_list_filter(self, request):
        """Nurse gets simplified filters (AC-02.2)."""
        if self._med_role(request) == "nurse":
            return ["status", "allergy_conflict"]
        return list(self.list_filter)

    # ── Queryset ─────────────────────────────────────────────────────

    def get_queryset(self, request):
        """Scope results by role (FR-D-4 / FR-N-2 / FR-Ph-1)."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not hasattr(request.user, "profile"):
            return qs.none()
        role = request.user.profile.role
        if role == "admin":
            return qs
        if role == "doctor":
            # Doctor sees medications for their assigned patients only
            return qs.filter(patient__assigned_doctor=request.user.profile).distinct()
        if role in ["nurse", "pharmacy"]:
            # Nurse: only assigned patients; pharmacy: all
            if role == "nurse":
                return qs.filter(patient__assigned_nurse=request.user.profile)
            return qs  # pharmacy sees all
        if role == "patient":
            return qs.filter(patient__user_profile=request.user.profile)
        return qs.none()

    # ── Module / object permissions ──────────────────────────────────

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        # Patients do not get a standalone Medication admin
        return request.user.profile.role in [
            "admin",
            "doctor",
            "nurse",
            "pharmacy",
        ]

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor"]

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role == "admin":
            return True
        if role == "doctor":
            if obj is None:
                return True
            return obj.patient.assigned_doctor == request.user.profile
        if role == "pharmacy":
            # Pharmacy can edit the notes field only (FR-Ph-2 / AC-02.1)
            return True
        return False

    def get_readonly_fields(self, request, obj=None):
        """Nurse: all fields read-only (AC-02.4); Pharmacy: clinical fields read-only."""
        base = list(self.readonly_fields)
        if not request.user.is_superuser and hasattr(request.user, "profile"):
            role = request.user.profile.role
            if role == "pharmacy":
                # Clinical prescription fields are read-only for pharmacy.
                # Writable:  notes (PBI-S3-02), fulfillment_status (PBI-S3-07)
                return base + [
                    "patient",
                    "medication_name",
                    "dosage",
                    "frequency",
                    "prescribing_doctor",
                    "start_date",
                    "end_date",
                    "status",
                ]
            if role == "nurse":
                # All fields read-only for nurse (AC-02.4)
                return base + [
                    "patient",
                    "medication_name",
                    "dosage",
                    "frequency",
                    "prescribing_doctor",
                    "start_date",
                    "end_date",
                    "status",
                    "fulfillment_status",
                    "notes",
                    "allergy_conflict",
                ]
        return base

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role == "admin"

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in [
            "admin",
            "doctor",
            "nurse",
            "pharmacy",
        ]

    # ── FK filtering and auto-set ─────────────────────────────────────

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "patient":
            if (
                not request.user.is_superuser
                and hasattr(request.user, "profile")
                and request.user.profile.role == "doctor"
            ):
                kwargs["queryset"] = Patient.objects.filter(
                    assigned_doctor=request.user.profile
                )
        if db_field.name == "prescribing_doctor":
            kwargs["queryset"] = UserProfile.objects.filter(role="doctor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-assign prescribing_doctor + audit-log create/update."""
        if (
            not obj.prescribing_doctor
            and hasattr(request.user, "profile")
            and request.user.profile.role == "doctor"
        ):
            obj.prescribing_doctor = request.user.profile
        if change and obj.pk:
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_data = _snapshot(old_obj)
            except self.model.DoesNotExist:
                old_data = {}
            super().save_model(request, obj, form, change)
            _write_audit_log(
                request, "update", obj, _build_changes_summary(old_data, _snapshot(obj))
            )
        else:
            super().save_model(request, obj, form, change)
            _write_audit_log(request, "create", obj)

    def delete_model(self, request, obj):
        """Audit-log delete."""
        _write_audit_log(request, "delete", obj)
        super().delete_model(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Audit-log read entry on medication detail page (AC-14.2)."""
        extra_context = extra_context or {}
        try:
            obj = self.get_object(request, object_id)
            if obj is not None:
                _write_audit_log(request, "read", obj)
                if obj.allergy_conflict:
                    extra_context["allergy_conflict_warning"] = True
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


# ── Appointment Admin ─────────────────────────────────────────────────────


class AppointmentTimeFilter(admin.SimpleListFilter):
    """
    Sidebar filter for patients: "Upcoming" vs "Past" appointments.

    Upcoming — future datetime AND status not completed/cancelled.
    Past      — past datetime OR status in completed/cancelled.
    """

    title = "time"
    parameter_name = "time"

    def lookups(self, request, model_admin):
        return [
            ("upcoming", "Upcoming"),
            ("past", "Past"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "upcoming":
            return queryset.filter(appointment_datetime__gte=now).exclude(
                status__in=["completed", "cancelled"]
            )
        if self.value() == "past":
            return queryset.filter(
                Q(appointment_datetime__lt=now)
                | Q(status__in=["completed", "cancelled"])
            )
        return queryset


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Appointment records.

    PBI-S3-09 — Admin full CRUD with status filter and date hierarchy.
    PBI-S3-10 — Patient read-only view scoped to own appointments (FR-P-4, FR-P-5).

    AC-09.1: Admin can create appointments; save redirects to changelist (HTTP 302)
    AC-09.2: Admin can edit status, notes, or location and persist changes
    AC-09.3: Admin can delete appointment records
    AC-09.4: Sidebar status filter on the changelist
    AC-09.5: Changelist columns: patient name, doctor name, appt date/time, type, status
    AC-10.1: Patient sees own upcoming appointments
    AC-10.2: Patient sees own past appointments
    AC-10.3: Patient sees zero appointments from other patients
    AC-10.4: Appointments ordered ascending by appointment_datetime
    AC-10.5: Detail view shows date, time, doctor full name, location
    AC-10.6: Patient view is read-only — no Save/Edit
    """

    list_display = [
        "get_patient_name",
        "get_doctor_name",
        "appointment_datetime",
        "appointment_type",
        "status",
    ]
    list_filter = ["status"]
    date_hierarchy = "appointment_datetime"
    search_fields = [
        "patient__user_profile__user__first_name",
        "patient__user_profile__user__last_name",
        "doctor__user__first_name",
        "doctor__user__last_name",
    ]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Appointment Details",
            {
                "fields": (
                    "patient",
                    "doctor",
                    "appointment_datetime",
                    "appointment_type",
                    "status",
                ),
            },
        ),
        (
            "Location & Notes",
            {
                "fields": ("location", "notes"),
            },
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Patient-facing fieldset: read-only, shows date/time, doctor, location (AC-10.5)
    _patient_fieldsets = (
        (
            "Your Appointment",
            {
                "fields": (
                    "appointment_datetime",
                    "appointment_type",
                    "status",
                    "get_doctor_full_name",
                    "location",
                    "notes",
                ),
                "description": "Your appointment details — read-only",
            },
        ),
    )

    # ── Display helpers ──────────────────────────────────────────────

    def get_patient_name(self, obj):
        """Display patient's full name."""
        return (
            obj.patient.user_profile.user.get_full_name()
            or obj.patient.user_profile.user.username
        )

    get_patient_name.short_description = "Patient"
    get_patient_name.admin_order_field = "patient__user_profile__user__last_name"

    def get_doctor_name(self, obj):
        """Display doctor's full name (changelist)."""
        if obj.doctor:
            return obj.doctor.user.get_full_name() or obj.doctor.user.username
        return "—"

    get_doctor_name.short_description = "Doctor"
    get_doctor_name.admin_order_field = "doctor__user__last_name"

    def get_doctor_full_name(self, obj):
        """Display doctor's full name in the detail view (AC-10.5)."""
        if obj and obj.doctor:
            return obj.doctor.user.get_full_name() or obj.doctor.user.username
        return "—"

    get_doctor_full_name.short_description = "Doctor"

    # ── Role helper ──────────────────────────────────────────────────

    def _role(self, request):
        return (
            getattr(request.user.profile, "role", None)
            if hasattr(request.user, "profile")
            else None
        )

    # ── Queryset ─────────────────────────────────────────────────────

    def get_queryset(self, request):
        """Scope queryset by role — FR-P-4 / FR-P-5 / FR-N-1 / PBI-S4-07."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not hasattr(request.user, "profile"):
            return qs.none()
        role = request.user.profile.role
        if role == "admin":
            return qs
        if role == "patient":
            request.user.profile.ensure_patient_record()
            return qs.filter(patient__user_profile=request.user.profile)
        if role == "nurse":
            return qs.filter(patient__assigned_nurse=request.user.profile)
        if role == "doctor":
            # AC-07.1: doctor sees only appointments for their assigned patients
            return qs.filter(patient__assigned_doctor=request.user.profile)
        return qs.none()

    # ── Permissions ──────────────────────────────────────────────────

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "patient", "nurse", "doctor"]

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role == "admin":
            return True
        if role == "doctor":
            if obj is None:
                return True
            # AC-07.3: object-level check
            return obj.patient.assigned_doctor == request.user.profile
        if role == "patient":
            if obj is None:
                return True
            return obj.patient.user_profile == request.user.profile
        if role == "nurse":
            if obj is None:
                return True
            return obj.patient.assigned_nurse == request.user.profile
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role in ["admin", "doctor"]

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        role = request.user.profile.role
        if role == "admin":
            return True
        if role == "doctor":
            if obj is None:
                return True
            # AC-07.3: only change appointments for own patients
            return obj.patient.assigned_doctor == request.user.profile
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role == "admin"

    # ── Role-aware overrides ──────────────────────────────────────────

    def get_list_filter(self, request):
        """Patients get time filter; doctor/nurse/admin get status filter (AC-07.4)."""
        if self._role(request) == "patient":
            return [AppointmentTimeFilter]
        return ["status"]

    def get_list_display(self, request):
        """Role-appropriate appointment list (AC-07.4 / AC-10.*)."""
        if self._role(request) == "patient":
            return [
                "appointment_datetime",
                "appointment_type",
                "get_doctor_name",
                "location",
                "status",
            ]
        if self._role(request) == "nurse":
            return [
                "get_patient_name",
                "appointment_datetime",
                "appointment_type",
                "get_doctor_name",
                "location",
                "status",
            ]
        return list(self.list_display)

    def get_readonly_fields(self, request, obj=None):
        """Patients and nurses: all read-only. Doctor: limited to editable fields."""
        if self._role(request) in ("patient", "nurse"):
            model_fields = [
                f.name for f in Appointment._meta.get_fields() if hasattr(f, "column")
            ]
            return list(set(model_fields + ["get_doctor_full_name"]))
        if self._role(request) == "doctor":
            # Doctor can edit notes, status, location, appointment_type (AC-07.2)
            # but cannot change patient or doctor assignment
            return list(self.readonly_fields) + [
                "patient",
                "doctor",
                "appointment_datetime",
            ]
        return list(self.readonly_fields)

    def get_fieldsets(self, request, obj=None):
        """Patients: read-only summary. Doctor: editable clinical fields. Admin: full."""
        if self._role(request) == "patient":
            return self._patient_fieldsets
        if self._role(request) == "doctor":
            return (
                (
                    "Appointment Details",
                    {
                        "fields": (
                            "patient",
                            "doctor",
                            "appointment_datetime",
                            "appointment_type",
                            "status",
                        ),
                        "description": "Patient and time are read-only. You can update status, type, location and notes.",
                    },
                ),
                (
                    "Location & Notes",
                    {"fields": ("location", "notes")},
                ),
            )
        return self.fieldsets

    # ── FK filtering ─────────────────────────────────────────────────

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict doctor FK dropdown; restrict patient dropdown for doctors."""
        if db_field.name == "doctor":
            kwargs["queryset"] = UserProfile.objects.filter(role="doctor")
        if db_field.name == "patient":
            if (
                not request.user.is_superuser
                and hasattr(request.user, "profile")
                and request.user.profile.role == "doctor"
            ):
                kwargs["queryset"] = Patient.objects.filter(
                    assigned_doctor=request.user.profile
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Audit-log create/update."""
        if change and obj.pk:
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_data = _snapshot(old_obj)
            except self.model.DoesNotExist:
                old_data = {}
            super().save_model(request, obj, form, change)
            _write_audit_log(
                request, "update", obj, _build_changes_summary(old_data, _snapshot(obj))
            )
        else:
            super().save_model(request, obj, form, change)
            _write_audit_log(request, "create", obj)

    def delete_model(self, request, obj):
        """Audit-log delete."""
        _write_audit_log(request, "delete", obj)
        super().delete_model(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Audit-log read (AC-14.2)."""
        extra_context = extra_context or {}
        try:
            obj = self.get_object(request, object_id)
            if obj is not None:
                _write_audit_log(request, "read", obj)
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


# ── Custom AdminSite: role-based navigation filtering + stats dashboard ──────


class CustomAdminSite(admin.AdminSite):
    """Admin site subclass: nurse navigation filter (AC-04.1)."""

    def get_app_list(self, request, app_label=None):
        """Restrict nurse navigation to patient-care sections only (AC-04.1)."""
        app_list = super().get_app_list(request, app_label=app_label)
        if not (
            hasattr(request.user, "profile") and request.user.profile.role == "nurse"
        ):
            return app_list
        nurse_allowed = {"Patient", "Medication", "Appointment", "TestResult"}
        filtered = []
        for app in app_list:
            models = [m for m in app["models"] if m["object_name"] in nurse_allowed]
            if models:
                filtered.append({**app, "models": models})
        return filtered


# Swap admin site class — preserves all existing registrations
admin.site.__class__ = CustomAdminSite

# ── Restrict Group admin to admins only (AC-04.2 / AC-11.1) ─────────────────

from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin  # noqa: E402

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


class CustomGroupAdmin(AdminOnlyMixin, BaseGroupAdmin):
    """Groups section limited to admin role only (AC-04.2 / AC-11.1/11.2)."""

    filter_horizontal = ("permissions",)

    def get_list_display(self, request):
        return ["name", "permission_count"]

    def permission_count(self, obj):
        return obj.permissions.count()

    permission_count.short_description = "Permission Count"

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, "profile"):
            return False
        return request.user.profile.role == "admin"


admin.site.register(Group, CustomGroupAdmin)


# Re-register UserAdmin with role-based functionality
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
