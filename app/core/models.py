from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import RegexValidator
from datetime import date


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
        # Auto-create Patient record for patient users
        if self.role == "patient":
            self.ensure_patient_record()
            # Ensure patient users can access admin interface
            if not self.user.is_staff:
                self.user.is_staff = True
                self.user.save()

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

    def ensure_patient_record(self):
        """Ensure a Patient record exists for this patient UserProfile."""
        if self.role == "patient":
            # Import here to avoid circular imports
            from datetime import date

            # Check if Patient record already exists
            if not hasattr(self, "patient_record"):
                try:
                    # Create a basic Patient record with placeholder data
                    # The user can fill in the actual details later through admin
                    Patient.objects.create(
                        user_profile=self,
                        date_of_birth=date(
                            1990, 1, 1
                        ),  # Placeholder - user should update
                        gender="O",  # Other - user should update
                        address_line1="Please update your address",
                        city="Please update",
                        state="Please update",
                        postal_code="00000",
                        phone_primary=self.phone or "000-000-0000",
                    )
                except Exception:
                    # Silent fail - Patient record creation is not critical for UserProfile creation
                    pass


class Patient(models.Model):
    """
    Patient model for storing detailed patient information.
    Links to UserProfile with role='patient'.
    """

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
        ("P", "Prefer not to say"),
    ]

    BLOOD_TYPE_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    ]

    # Link to UserProfile
    user_profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="patient_record"
    )

    # Medical identification
    medical_id = models.CharField(
        max_length=20, unique=True, help_text="Unique medical record identifier"
    )

    # Personal information
    date_of_birth = models.DateField(help_text="Patient's date of birth")

    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, help_text="Patient's gender"
    )

    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Patient's blood type (if known)",
    )

    # Insurance information
    insurance_number = models.CharField(
        max_length=50, blank=True, null=True, help_text="Health insurance policy number"
    )

    # Contact information
    address_line1 = models.CharField(max_length=255, help_text="Primary address line")

    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Secondary address line (apartment, suite, etc.)",
    )

    city = models.CharField(max_length=100, help_text="City")

    state = models.CharField(max_length=50, help_text="State or province")

    postal_code = models.CharField(max_length=20, help_text="Postal or ZIP code")

    country = models.CharField(
        max_length=100, default="United States", help_text="Country"
    )

    # Phone validation pattern
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    phone_primary = models.CharField(
        validators=[phone_regex], max_length=17, help_text="Primary phone number"
    )

    phone_secondary = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        help_text="Secondary phone number (optional)",
    )

    email_personal = models.EmailField(
        blank=True,
        null=True,
        help_text="Personal email address (separate from login email)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["medical_id"]
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return f"{self.medical_id} - {self.user_profile.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate medical ID if not provided
        if not self.medical_id:
            self.medical_id = self.generate_medical_id()

        # Validate that linked UserProfile has patient role
        if self.user_profile.role != "patient":
            raise ValidationError(
                "Patient records can only be linked to UserProfiles with role='patient'"
            )

        # Validate date of birth
        self.clean_date_of_birth()

        super().save(*args, **kwargs)

    def generate_medical_id(self):
        """Generate unique medical ID in format PMR-YYYY-NNNNNN"""
        current_year = timezone.now().year

        # Get the last patient ID for this year
        last_patient = (
            Patient.objects.filter(medical_id__startswith=f"PMR-{current_year}-")
            .order_by("-medical_id")
            .first()
        )

        if last_patient:
            # Extract the sequence number and increment
            last_sequence = int(last_patient.medical_id.split("-")[-1])
            new_sequence = last_sequence + 1
        else:
            # First patient of the year
            new_sequence = 1

        return f"PMR-{current_year}-{new_sequence:06d}"

    def clean_date_of_birth(self):
        """Validate date of birth"""
        if self.date_of_birth > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

        # Check for reasonable age limits (0-120 years)
        age_years = (date.today() - self.date_of_birth).days / 365.25
        if age_years > 120:
            raise ValidationError("Date of birth indicates an unrealistic age.")

    @property
    def age(self):
        """Calculate patient's current age"""
        today = date.today()
        age = (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )
        return age

    @property
    def full_address(self):
        """Return formatted full address"""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([self.city, self.state, self.postal_code, self.country])
        return ", ".join(address_parts)

    def get_emergency_contacts(self):
        """Get all emergency contacts ordered by primary status"""
        return self.emergency_contacts.all().order_by("-is_primary_contact", "name")

    def get_primary_emergency_contact(self):
        """Get the primary emergency contact"""
        return self.emergency_contacts.filter(is_primary_contact=True).first()


class EmergencyContact(models.Model):
    """
    Emergency contact information for patients.
    Multiple emergency contacts allowed per patient.
    """

    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse"),
        ("parent", "Parent"),
        ("child", "Child"),
        ("sibling", "Sibling"),
        ("grandparent", "Grandparent"),
        ("grandchild", "Grandchild"),
        ("friend", "Friend"),
        ("neighbor", "Neighbor"),
        ("caregiver", "Caregiver"),
        ("other", "Other"),
    ]

    # Link to patient
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="emergency_contacts"
    )

    # Contact information
    name = models.CharField(max_length=100, help_text="Emergency contact's full name")

    relationship = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES, help_text="Relationship to patient"
    )

    # Phone validation (reuse from Patient model)
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    phone_primary = models.CharField(
        validators=[phone_regex], max_length=17, help_text="Primary phone number"
    )

    phone_secondary = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        help_text="Secondary phone number (optional)",
    )

    email = models.EmailField(
        blank=True, null=True, help_text="Email address (optional)"
    )

    # Priority and status
    is_primary_contact = models.BooleanField(
        default=False, help_text="Primary emergency contact"
    )

    # Additional information
    notes = models.TextField(
        blank=True, null=True, help_text="Additional notes about this contact"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary_contact", "name"]
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        primary_indicator = " (Primary)" if self.is_primary_contact else ""
        return f"{self.name} - {self.get_relationship_display()}{primary_indicator}"

    def save(self, *args, **kwargs):
        # Ensure only one primary contact per patient
        if self.is_primary_contact:
            EmergencyContact.objects.filter(
                patient=self.patient, is_primary_contact=True
            ).exclude(pk=self.pk).update(is_primary_contact=False)

        super().save(*args, **kwargs)


# Signal handlers removed - profile creation and group assignment
# handled directly in admin forms and model save methods
