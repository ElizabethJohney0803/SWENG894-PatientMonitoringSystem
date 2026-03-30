from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import UserProfile


class Command(BaseCommand):
    help = "Set up user groups and permissions for Patient Monitoring System"

    def handle(self, *args, **options):
        self.stdout.write("Setting up groups and permissions...")

        # Define groups and their permissions
        groups_permissions = {
            "Patients": {
                "description": "Patients can view their own records only",
                "permissions": [
                    ("view_userprofile", "core", "userprofile"),
                    ("change_userprofile", "core", "userprofile"),  # Own profile only
                ],
            },
            "Doctors": {
                "description": "Doctors can manage assigned patients and medical records",
                "permissions": [
                    ("view_userprofile", "core", "userprofile"),
                    ("change_userprofile", "core", "userprofile"),
                    ("add_userprofile", "core", "userprofile"),
                ],
            },
            "Nurses": {
                "description": "Nurses can view and update patient care information",
                "permissions": [
                    ("view_userprofile", "core", "userprofile"),
                    ("change_userprofile", "core", "userprofile"),
                ],
            },
            "Pharmacy": {
                "description": "Pharmacy personnel can manage medications and prescriptions",
                "permissions": [
                    ("view_userprofile", "core", "userprofile"),
                ],
            },
            "Administrators": {
                "description": "System administrators have full access",
                "permissions": [
                    ("view_userprofile", "core", "userprofile"),
                    ("add_userprofile", "core", "userprofile"),
                    ("change_userprofile", "core", "userprofile"),
                    ("delete_userprofile", "core", "userprofile"),
                ],
            },
        }

        for group_name, group_data in groups_permissions.items():
            # Create or get group
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                self.stdout.write(f"Created group: {group_name}")
            else:
                self.stdout.write(f"Group already exists: {group_name}")

            # Clear existing permissions
            group.permissions.clear()

            # Add permissions to group
            for perm_codename, app_label, model_name in group_data["permissions"]:
                try:
                    content_type = ContentType.objects.get(
                        app_label=app_label, model=model_name
                    )
                    permission = Permission.objects.get(
                        codename=perm_codename, content_type=content_type
                    )
                    group.permissions.add(permission)
                    self.stdout.write(
                        f"  Added permission: {perm_codename} to {group_name}"
                    )
                except (ContentType.DoesNotExist, Permission.DoesNotExist) as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Permission not found: {perm_codename} - {e}"
                        )
                    )

        # Assign existing users to appropriate groups based on their roles
        self.assign_users_to_groups()

        self.stdout.write(
            self.style.SUCCESS("Successfully set up groups and permissions!")
        )

    def assign_users_to_groups(self):
        """Assign existing users to groups based on their profile roles."""
        role_to_group = {
            "patient": "Patients",
            "doctor": "Doctors",
            "nurse": "Nurses",
            "pharmacy": "Pharmacy",
            "admin": "Administrators",
        }

        for profile in UserProfile.objects.all():
            group_name = role_to_group.get(profile.role)
            if group_name:
                try:
                    group = Group.objects.get(name=group_name)
                    profile.user.groups.clear()
                    profile.user.groups.add(group)
                    self.stdout.write(
                        f"Assigned {profile.user.username} to {group_name} group"
                    )
                except Group.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Group {group_name} not found for {profile.user.username}"
                        )
                    )
