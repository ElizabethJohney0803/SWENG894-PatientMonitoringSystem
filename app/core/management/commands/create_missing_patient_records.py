"""
Django management command to create missing Patient records.
This helps existing patient UserProfiles that don't have corresponding Patient records.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import UserProfile, Patient, EmergencyContact
from datetime import date


class Command(BaseCommand):
    help = "Create Patient records for existing patient UserProfiles and ensure they have admin access"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating records",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No records will be created")
            )

        # Find patient UserProfiles without Patient records
        patient_profiles = UserProfile.objects.filter(role="patient")
        missing_patient_records = []
        need_staff_status = []

        for profile in patient_profiles:
            if not hasattr(profile, "patient_record"):
                missing_patient_records.append(profile)
            # Also check if patient user needs staff status for admin access
            if not profile.user.is_staff:
                need_staff_status.append(profile)

        # Handle missing Patient records
        if not missing_patient_records:
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ All patient UserProfiles already have Patient records!"
                )
            )
        else:
            self.stdout.write(
                f"Found {len(missing_patient_records)} patient profiles missing Patient records:"
            )

        # Handle staff status updates
        if need_staff_status:
            self.stdout.write(
                f"Found {len(need_staff_status)} patient users needing staff status for admin access:"
            )

        created_count = 0
        staff_updated_count = 0

        # Create missing Patient records
        for profile in missing_patient_records:
            user = profile.user
            self.stdout.write(
                f"  • {user.get_full_name() or user.username} (ID: {user.id}) - Missing Patient record"
            )

            if not dry_run:
                try:
                    # Create Patient record with placeholder data
                    patient = Patient.objects.create(
                        user_profile=profile,
                        date_of_birth=date(1990, 1, 1),  # Placeholder
                        gender="O",  # Other - needs to be updated
                        address_line1="Please update your address",
                        city="Please update",
                        state="Please update",
                        postal_code="00000",
                        phone_primary=profile.phone or "000-000-0000",
                    )
                    created_count += 1
                    self.stdout.write(
                        f"    ✅ Created Patient record {patient.medical_id}"
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ❌ Failed to create Patient record: {str(e)}"
                        )
                    )

        # Update staff status for patient users
        for profile in need_staff_status:
            user = profile.user
            self.stdout.write(
                f"  • {user.get_full_name() or user.username} (ID: {user.id}) - Needs staff status"
            )

            if not dry_run:
                try:
                    user.is_staff = True
                    user.save()
                    staff_updated_count += 1
                    self.stdout.write(f"    ✅ Granted admin access (staff status)")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ❌ Failed to update staff status: {str(e)}"
                        )
                    )

        if dry_run:
            total_operations = len(missing_patient_records) + len(need_staff_status)
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would perform {total_operations} operations:"
                )
            )
            if missing_patient_records:
                self.stdout.write(
                    f"  - Create {len(missing_patient_records)} Patient records"
                )
            if need_staff_status:
                self.stdout.write(
                    f"  - Update {len(need_staff_status)} users with staff status"
                )
            self.stdout.write(
                "Run without --dry-run to actually perform these operations"
            )
        else:
            self.stdout.write(
                f"✅ Successfully created {created_count} Patient records"
            )
            self.stdout.write(
                f"✅ Successfully updated {staff_updated_count} users with staff status"
            )

            total_failed = (
                len(missing_patient_records)
                - created_count
                + len(need_staff_status)
                - staff_updated_count
            )
            if total_failed > 0:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  {total_failed} operations failed")
                )

            self.stdout.write("\n📋 Next Steps:")
            self.stdout.write("1. Patient users can now log into admin interface")
            self.stdout.write(
                "2. They should update placeholder data with actual information"
            )
            self.stdout.write("3. Emergency contact information should be added")
            self.stdout.write("4. Test patient login to verify admin access works")
