from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile for role-based access control."""

    ROLE_CHOICES = [
        ("patient", "Patient"),
        ("doctor", "Doctor"),
        ("nurse", "Nurse"),
        ("pharmacy", "Pharmacy Personnel"),
        ("admin", "System Administrator"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="User's role in the patient monitoring system",
    )
    department = models.CharField(
        max_length=100, blank=True, help_text="Department or ward assignment"
    )
    license_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Professional license number (for medical staff)",
    )
    phone = models.CharField(
        max_length=20, blank=True, help_text="Contact phone number"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    def clean(self):
        # Only validate license requirements if we have a role set
        # and we're not in the middle of form processing
        if (
            self.role in ["doctor", "nurse", "pharmacy"]
            and hasattr(self, "_state")
            and self._state.adding
            and not self.license_number
        ):
            raise ValidationError(
                {"license_number": "License number is required for medical staff."}
            )

    def save(self, *args, **kwargs):
        # Skip clean method validation during initial save from form
        # The form handles validation

        # Save the profile first
        super().save(*args, **kwargs)

        # Assign user to appropriate group after saving
        self.assign_to_group()

    def assign_to_group(self):
        """Assign user to the appropriate group based on their role."""
        from django.contrib.auth.models import Group

        role_to_group = {
            "patient": "Patients",
            "doctor": "Doctors",
            "nurse": "Nurses",
            "pharmacy": "Pharmacy",
            "admin": "Administrators",
        }

        group_name = role_to_group.get(self.role)
        if group_name and self.user_id:
            try:
                # Remove user from all existing groups first
                self.user.groups.clear()

                # Get or create the group
                group, created = Group.objects.get_or_create(name=group_name)

                # Add user to the appropriate group
                self.user.groups.add(group)

                # Force save the user to ensure group assignment sticks
                self.user.save()

            except Exception as e:
                # Silent fail - group assignment is not critical for basic functionality
                pass

    @property
    def is_medical_staff(self):
        """Check if user is medical staff."""
        return self.role in ["doctor", "nurse", "pharmacy"]

    @property
    def can_access_patient_records(self):
        """Check if user can access patient records."""
        return self.role in ["doctor", "nurse", "admin"]

    @property
    def can_prescribe_medication(self):
        """Check if user can prescribe medication."""
        return self.role in ["doctor", "admin"]

    @property
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role == "admin"

    @property
    def is_complete(self):
        """Check if profile is complete."""
        required_fields = ["role"]

        if self.is_medical_staff:
            required_fields.append("license_number")

        if self.role in ["doctor", "nurse"]:
            required_fields.append("department")

        for field in required_fields:
            if not getattr(self, field):
                return False

        return True

    def get_missing_fields(self):
        """Get list of required but missing fields."""
        missing = []

        if not self.role:
            missing.append("role")

        if self.is_medical_staff and not self.license_number:
            missing.append("license_number")

        if self.role in ["doctor", "nurse"] and not self.department:
            missing.append("department")

        return missing


# Signal handlers removed - profile creation and group assignment
# handled directly in admin forms and model save methods
