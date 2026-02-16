from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.db import models
from .models import UserProfile, Patient, EmergencyContact
from .mixins import PatientAccessMixin, AdminOnlyMixin


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

    def has_module_permission(self, request):
        """Allow admin users and superusers to access user management module."""
        # Always allow superusers
        if request.user.is_superuser:
            return True

        # Allow users with admin role
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True

        # Fall back to default Django permission check
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
        """Override save_model to handle profile creation properly."""
        super().save_model(request, obj, form, change)

        # For new users, the form's save method should have already created the profile
        # Ensure the profile exists and has the correct data
        if not change and not hasattr(obj, "profile"):
            # This shouldn't happen, but just in case
            from core.models import UserProfile

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
        """Make fields readonly for patients viewing their own records."""
        if hasattr(request.user, "profile") and request.user.profile.role == "patient":
            if obj and obj.user_profile != request.user.profile:
                # Patient trying to view another patient's data
                return list(self.fields)
        return []


@admin.register(Patient)
class PatientAdmin(PatientAccessMixin, admin.ModelAdmin):
    """Admin interface for patient records with role-based access."""

    list_display = [
        "medical_id",
        "get_patient_name",
        "age",
        "gender",
        "phone_primary",
        "city",
        "state",
        "created_at",
    ]
    list_filter = ["gender", "blood_type", "state", "created_at", "updated_at"]
    search_fields = [
        "medical_id",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "user_profile__user__username",
        "phone_primary",
        "city",
        "insurance_number",
    ]
    readonly_fields = ["medical_id", "age", "created_at", "updated_at"]

    fieldsets = (
        ("Patient Identity", {"fields": ("user_profile", "medical_id")}),
        (
            "Personal Information",
            {"fields": ("date_of_birth", "gender", "blood_type", "insurance_number")},
        ),
        (
            "Contact Information",
            {"fields": ("phone_primary", "phone_secondary", "email_personal")},
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
                )
            },
        ),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [EmergencyContactInline]

    def get_patient_name(self, obj):
        """Display patient's full name."""
        return obj.user_profile.user.get_full_name() or obj.user_profile.user.username

    get_patient_name.short_description = "Patient Name"
    get_patient_name.admin_order_field = "user_profile__user__last_name"

    def age(self, obj):
        """Display patient's age."""
        return obj.age

    age.short_description = "Age"

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
            # Patients can only see their own record
            return qs.filter(user_profile=request.user.profile)
        elif user_role in ["doctor", "nurse", "pharmacy"]:
            # Medical staff can see all patients
            return qs
        else:
            # Other roles see nothing
            return qs.none()

    def get_readonly_fields(self, request, obj=None):
        """Set readonly fields based on user role."""
        readonly_fields = list(self.readonly_fields)

        if hasattr(request.user, "profile") and request.user.profile.role == "patient":
            # Patients can only edit limited fields
            if obj and obj.user_profile != request.user.profile:
                # Patient trying to edit another patient's record - make all readonly
                return [field.name for field in self.model._meta.fields]
            else:
                # Patient editing their own record - some fields editable
                readonly_fields.extend(["user_profile", "date_of_birth", "gender"])

        return readonly_fields

    def has_add_permission(self, request):
        """Control who can add new patient records."""
        # Use the permission from PatientAccessMixin
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Control who can change patient records."""
        if not super().has_change_permission(request, obj):
            return False

        # Additional checks for patients
        if hasattr(request.user, "profile") and request.user.profile.role == "patient":
            if obj and obj.user_profile != request.user.profile:
                return False  # Patients can't edit other patients' records

        return True

    def has_delete_permission(self, request, obj=None):
        """Control who can delete patient records."""
        # Use the permission from PatientAccessMixin
        return super().has_delete_permission(request, obj)


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
        elif user_role in ["doctor", "nurse", "pharmacy"]:
            # Medical staff can see all emergency contacts
            return qs
        else:
            # Other roles see nothing
            return qs.none()


# Re-register UserAdmin with role-based functionality
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
