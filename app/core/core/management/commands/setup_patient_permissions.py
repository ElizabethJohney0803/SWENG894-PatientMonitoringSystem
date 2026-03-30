"""
Django management command to set up proper permissions for patient users.
Ensures patients can access their Patient records through Django admin.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Patient, EmergencyContact


class Command(BaseCommand):
    help = (
        "Set up proper permissions for patient users to access Patient records in admin"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating permissions",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No permissions will be created")
            )

        # Get or create Patients group
        patients_group, created = Group.objects.get_or_create(name="Patients")

        if created:
            self.stdout.write('✅ Created "Patients" group')
        else:
            self.stdout.write('✅ "Patients" group already exists')

        # Get content types
        patient_ct = ContentType.objects.get_for_model(Patient)
        emergency_contact_ct = ContentType.objects.get_for_model(EmergencyContact)

        # Define permissions needed for patients
        permissions_to_add = [
            # Patient model permissions
            ("view_patient", patient_ct, "Can view patient records"),
            ("change_patient", patient_ct, "Can change patient records"),
            # Emergency contact permissions
            (
                "view_emergencycontact",
                emergency_contact_ct,
                "Can view emergency contacts",
            ),
            (
                "add_emergencycontact",
                emergency_contact_ct,
                "Can add emergency contacts",
            ),
            (
                "change_emergencycontact",
                emergency_contact_ct,
                "Can change emergency contacts",
            ),
            (
                "delete_emergencycontact",
                emergency_contact_ct,
                "Can delete emergency contacts",
            ),
        ]

        added_permissions = 0

        for perm_codename, content_type, perm_name in permissions_to_add:
            # Get or create the permission
            permission, perm_created = Permission.objects.get_or_create(
                codename=perm_codename,
                content_type=content_type,
                defaults={"name": perm_name},
            )

            if perm_created:
                self.stdout.write(f"   Created permission: {perm_codename}")

            # Add permission to Patients group if not already added
            if not patients_group.permissions.filter(pk=permission.pk).exists():
                if not dry_run:
                    patients_group.permissions.add(permission)
                    added_permissions += 1
                    self.stdout.write(f"   ✅ Added {perm_codename} to Patients group")
                else:
                    self.stdout.write(f"   Would add {perm_codename} to Patients group")
            else:
                self.stdout.write(f"   ✓ {perm_codename} already in Patients group")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would add {len(permissions_to_add)} permissions to Patients group"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Successfully configured {len(permissions_to_add)} permissions for Patients group"
                )
            )

            # Verify current group permissions
            current_perms = patients_group.permissions.all()
            self.stdout.write(
                f"\n📋 Patients group now has {current_perms.count()} permissions:"
            )
            for perm in current_perms:
                self.stdout.write(f"   • {perm.codename} - {perm.name}")

            self.stdout.write("\n🎉 Patient users can now:")
            self.stdout.write("   • View their own Patient records in admin")
            self.stdout.write("   • Edit their own Patient information")
            self.stdout.write("   • Add/edit/delete their emergency contacts")
            self.stdout.write("   • Access Patient admin module")
