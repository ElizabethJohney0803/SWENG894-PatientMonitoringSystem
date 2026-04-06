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
    def can_assign_patients(self):
        """Check if user can assign patients to doctors."""
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

    def get_assigned_patients(self):
        """Get all patients assigned to this doctor."""
        if self.role == "doctor":
            return self.assigned_patients.all()
        return None

    def get_assigned_patients_count(self):
        """Get count of patients assigned to this doctor."""
        if self.role == "doctor":
            return self.assigned_patients.count()
        return 0


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

    # Doctor assignment (admin-only)
    assigned_doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
        related_name="assigned_patients",
        help_text="Doctor assigned to this patient (admin-only assignment)",
    )

    # Nurse assignment (admin-only) — FR-N-1
    assigned_nurse = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "nurse"},
        related_name="assigned_nurse_patients",
        help_text="Nurse assigned to this patient (admin-only assignment)",
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

    # Medical History fields (PMS-014) — FR-D-4
    diagnoses = models.TextField(
        blank=True,
        help_text=(
            "Current and past diagnoses — editable by Doctor/Admin, "
            "read-only for Nurse, hidden from Patient"
        ),
    )
    procedures = models.TextField(
        blank=True,
        help_text=(
            "Surgical and clinical procedures performed — "
            "read-only for Nurse, hidden from Patient"
        ),
    )
    visit_notes = models.TextField(
        blank=True,
        help_text=(
            "Prior visit notes and clinical observations — "
            "read-only for Nurse, hidden from Patient"
        ),
    )
    allergies = models.TextField(
        blank=True,
        help_text=(
            "Known allergies (medications, food, environmental) — "
            "visible to Doctor/Nurse/Pharmacy/Admin, hidden from Patient "
            "in admin — FR-Ph-3"
        ),
    )
    chronic_conditions = models.TextField(
        blank=True,
        help_text=(
            "Long-term chronic conditions — " "read-only for Nurse, hidden from Patient"
        ),
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

        # Validate assigned doctor
        if self.assigned_doctor and self.assigned_doctor.role != "doctor":
            raise ValidationError("Assigned doctor must have role='doctor'")

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


class Medication(models.Model):
    """
    Medication records linked to a patient and prescribing doctor.

    FR-D-5: Doctor can view current and past medications of assigned patients.
    FR-N-2: Nurse can view current medications of assigned patients.
    FR-Ph-1/2: Pharmacy can view medication orders for patients.
    """

    STATUS_CHOICES = [
        ("current", "Current"),
        ("past", "Past"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medications",
        help_text="Patient this medication belongs to",
    )
    prescribing_doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
        related_name="prescribed_medications",
        help_text="Doctor who prescribed this medication",
    )
    medication_name = models.CharField(
        max_length=200,
        help_text="Name of the medication (e.g. Metformin)",
    )
    dosage = models.CharField(
        max_length=100,
        help_text="Dosage (e.g. 500 mg)",
    )
    frequency = models.CharField(
        max_length=100,
        help_text="Frequency (e.g. Twice daily)",
    )
    start_date = models.DateField(
        help_text="Date the medication was started",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the medication was stopped (blank = ongoing)",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="current",
        help_text="Whether the medication is currently active",
    )
    FULFILLMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("dispensed", "Dispensed"),
        ("cancelled", "Cancelled"),
    ]

    notes = models.TextField(
        blank=True,
        help_text="Additional notes or instructions",
    )
    fulfillment_status = models.CharField(
        max_length=15,
        choices=FULFILLMENT_STATUS_CHOICES,
        default="pending",
        help_text=("Prescription fulfillment lifecycle status — FR-D-5 / FR-Ph-1"),
    )
    allergy_conflict = models.BooleanField(
        default=False,
        help_text=(
            "Automatically set to True when the medication name matches an entry "
            "in the patient's recorded allergies — FR-Ph-4"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-start_date"]
        verbose_name = "Medication"
        verbose_name_plural = "Medications"

    def __str__(self):
        return (
            f"{self.medication_name} ({self.dosage}) "
            f"\u2014 {self.get_status_display()}"
        )

    def _check_allergy_conflict(self):
        """
        Return True if medication_name matches any entry in the patient's
        allergies field (case-insensitive).  Returns False for blank/null
        allergies so no false positives are generated.
        """
        allergies_raw = getattr(self.patient, "allergies", "") or ""
        if not allergies_raw.strip():
            return False
        med_name = self.medication_name.lower()
        for allergy in allergies_raw.split(","):
            if (
                allergy.strip().lower() in med_name
                or med_name in allergy.strip().lower()
            ):
                return True
        return False

    def save(self, *args, **kwargs):
        self.allergy_conflict = self._check_allergy_conflict()
        super().save(*args, **kwargs)

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.prescribing_doctor and self.prescribing_doctor.role != "doctor":
            raise ValidationError(
                {"prescribing_doctor": ("Prescribing doctor must have role='doctor'.")}
            )


class TestResult(models.Model):
    """
    Laboratory and clinical test results linked to a patient and doctor.

    FR-P-1: Patient can view their own test results.
    FR-P-2: Display test name, result value, reference range, date.
    FR-P-3: Patients cannot see other patients' results.
    FR-D-1: Doctor can view test results of assigned patients.
    FR-D-3: Results displayed chronologically per patient.
    """

    TEST_TYPE_CHOICES = [
        ("blood_panel", "Blood Panel"),
        ("metabolic_panel", "Metabolic Panel"),
        ("urinalysis", "Urinalysis"),
        ("hormone_panel", "Hormone Panel"),
        ("lipid_panel", "Lipid Panel"),
        ("imaging", "Imaging"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("normal", "Normal"),
        ("low", "Low"),
        ("high", "High"),
        ("critical", "Critical"),
        ("pending", "Pending"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="test_results",
        help_text="Patient this test result belongs to",
    )
    ordering_doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
        related_name="ordered_tests",
        help_text="Doctor who ordered this test",
    )
    test_name = models.CharField(
        max_length=200,
        help_text="Name of the test (e.g. Complete Blood Count)",
    )
    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default="other",
        help_text="Category of the test",
    )
    test_date = models.DateField(
        help_text="Date the test was performed",
    )
    result_value = models.CharField(
        max_length=100,
        help_text="Result value (e.g. '7.2', 'Negative', '14.5')",
    )
    result_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit of measurement (e.g. g/dL, mg/dL)",
    )
    reference_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Normal reference range (e.g. '12.0-17.5 g/dL')",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Result status relative to reference range",
    )
    doctor_notes = models.TextField(
        blank=True,
        help_text="Doctor's notes and interpretation of the results",
    )
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Indicates whether a follow-up appointment is required",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-test_date", "-created_at"]
        verbose_name = "Test Result"
        verbose_name_plural = "Test Results"

    def __str__(self):
        patient_name = self.patient.user_profile.user.get_full_name()
        return f"{self.test_name} \u2014 {patient_name} ({self.test_date})"

    def clean(self):
        if self.test_date and self.test_date > date.today():
            raise ValidationError({"test_date": "Test date cannot be in the future."})
        if self.ordering_doctor and self.ordering_doctor.role != "doctor":
            raise ValidationError(
                {"ordering_doctor": ("Ordering doctor must have role='doctor'.")}
            )


class Appointment(models.Model):
    """
    Appointment records linking a patient to a doctor.

    FR-P-4: Patient can view their own appointments.
    FR-P-5: Appointment detail shows date, time, doctor, and location.
    """

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ]

    APPOINTMENT_TYPE_CHOICES = [
        ("initial_consultation", "Initial Consultation"),
        ("follow_up", "Follow-Up"),
        ("routine_checkup", "Routine Check-Up"),
        ("lab_review", "Lab Review"),
        ("urgent_care", "Urgent Care"),
    ]

    VALID_STATUSES = {c[0] for c in STATUS_CHOICES}
    VALID_APPOINTMENT_TYPES = {c[0] for c in APPOINTMENT_TYPE_CHOICES}

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
        help_text="Patient for this appointment",
    )
    doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "doctor"},
        related_name="doctor_appointments",
        help_text="Doctor responsible for this appointment",
    )
    appointment_datetime = models.DateTimeField(
        help_text="Scheduled date and time of the appointment",
    )
    appointment_type = models.CharField(
        max_length=30,
        choices=APPOINTMENT_TYPE_CHOICES,
        help_text="Category of appointment",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="scheduled",
        help_text="Current status of the appointment",
    )
    location = models.CharField(
        max_length=200,
        help_text="Room or clinic name where the appointment takes place",
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional clinical or administrative notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["appointment_datetime"]
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"

    def __str__(self):
        patient_name = self.patient.user_profile.user.get_full_name()
        appt_date = self.appointment_datetime.strftime("%Y-%m-%d %H:%M")
        return f"{patient_name} — {appt_date}"

    def clean(self):
        if self.status not in self.VALID_STATUSES:
            raise ValidationError(
                {"status": f"'{self.status}' is not a valid status choice."}
            )
        if self.appointment_type not in self.VALID_APPOINTMENT_TYPES:
            raise ValidationError(
                {
                    "appointment_type": (
                        f"'{self.appointment_type}' is not a valid " "appointment type."
                    )
                }
            )


# Signal handlers removed - profile creation and group assignment
# handled directly in admin forms and model save methods
