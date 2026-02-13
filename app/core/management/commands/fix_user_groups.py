from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = "Fix user group assignments based on their profile roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        profiles = UserProfile.objects.all()
        fixed_count = 0

        for profile in profiles:
            # Get current groups
            current_groups = list(profile.user.groups.values_list("name", flat=True))

            # Determine what the correct group should be
            role_to_group = {
                "patient": "Patients",
                "doctor": "Doctors",
                "nurse": "Nurses",
                "pharmacy": "Pharmacy",
                "admin": "Administrators",
            }

            expected_group = role_to_group.get(profile.role)

            if expected_group and expected_group not in current_groups:
                self.stdout.write(
                    f"User {profile.user.username} (Role: {profile.role}) "
                    f"has groups {current_groups}, should be in [{expected_group}]"
                )

                if not dry_run:
                    profile.assign_to_group()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Fixed group assignment for {profile.user.username}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  → Would fix group assignment for {profile.user.username}"
                        )
                    )
            elif expected_group and expected_group in current_groups:
                self.stdout.write(
                    f"User {profile.user.username} (Role: {profile.role}) already in correct group"
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Fixed group assignments for {fixed_count} users")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Would fix group assignments for users shown above")
            )
