from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


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
        if self.role in ["doctor", "nurse", "pharmacy"] and not self.license_number:
            raise ValidationError(
                {"license_number": "License number is required for medical staff."}
            )
