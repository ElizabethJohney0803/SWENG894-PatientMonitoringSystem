from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, Patient


class Command(BaseCommand):
    help = (
        "Assign doctors to patients for testing Patient-Doctor assignment functionality"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--doctor-username",
            type=str,
            help="Username of doctor to assign patients to",
        )
        parser.add_argument(
            "--assign-all-unassigned",
            action="store_true",
            help="Assign all unassigned patients to the specified doctor",
        )
        parser.add_argument(
            "--list-unassigned",
            action="store_true",
            help="List all patients without assigned doctors",
        )
        parser.add_argument(
            "--list-doctors", action="store_true", help="List all available doctors"
        )

    def handle(self, *args, **options):
        if options["list_doctors"]:
            self.list_doctors()
            return

        if options["list_unassigned"]:
            self.list_unassigned_patients()
            return

        if options["assign_all_unassigned"]:
            if not options["doctor_username"]:
                self.stdout.write(
                    self.style.ERROR(
                        "--doctor-username is required when using --assign-all-unassigned"
                    )
                )
                return
            self.assign_all_unassigned(options["doctor_username"])
            return

        self.stdout.write(
            self.style.WARNING(
                "Please specify an action. Use --help for available options."
            )
        )

    def list_doctors(self):
        """List all available doctors."""
        doctors = UserProfile.objects.filter(role="doctor").select_related("user")

        if not doctors:
            self.stdout.write(self.style.WARNING("No doctors found in the system."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {doctors.count()} doctors:"))
        for doctor in doctors:
            assigned_count = doctor.assigned_patients.count()
            self.stdout.write(
                f"  - {doctor.user.username}: {doctor.user.get_full_name()} "
                f'(Department: {doctor.department or "None"}, '
                f'License: {doctor.license_number or "None"}, '
                f"Assigned Patients: {assigned_count})"
            )

    def list_unassigned_patients(self):
        """List all patients without assigned doctors."""
        unassigned_patients = Patient.objects.filter(
            assigned_doctor__isnull=True
        ).select_related("user_profile__user")

        if not unassigned_patients:
            self.stdout.write(self.style.SUCCESS("All patients have assigned doctors."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found {unassigned_patients.count()} unassigned patients:"
            )
        )
        for patient in unassigned_patients:
            self.stdout.write(
                f"  - {patient.medical_id}: {patient.user_profile.user.get_full_name()} "
                f"({patient.user_profile.user.username})"
            )

    def assign_all_unassigned(self, doctor_username):
        """Assign all unassigned patients to the specified doctor."""
        try:
            doctor_user = User.objects.get(username=doctor_username)
            doctor_profile = doctor_user.profile

            if doctor_profile.role != "doctor":
                self.stdout.write(
                    self.style.ERROR(
                        f"User {doctor_username} is not a doctor (role: {doctor_profile.role})"
                    )
                )
                return

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Doctor with username {doctor_username} not found.")
            )
            return

        unassigned_patients = Patient.objects.filter(assigned_doctor__isnull=True)

        if not unassigned_patients:
            self.stdout.write(self.style.SUCCESS("No unassigned patients found."))
            return

        count = unassigned_patients.count()
        unassigned_patients.update(assigned_doctor=doctor_profile)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned {count} patients to Dr. {doctor_profile.user.get_full_name()} "
                f"({doctor_username})"
            )
        )

        # Show updated assignment count
        total_assigned = doctor_profile.assigned_patients.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Dr. {doctor_profile.user.get_full_name()} now has {total_assigned} assigned patients."
            )
        )
