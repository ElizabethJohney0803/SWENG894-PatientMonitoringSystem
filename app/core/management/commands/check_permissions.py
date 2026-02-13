from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = "Check user permissions and access levels"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== User Access Report ==="))

        profiles = UserProfile.objects.all()

        for profile in profiles:
            groups = list(profile.user.groups.values_list("name", flat=True))

            self.stdout.write(f"\nUser: {profile.user.username}")
            self.stdout.write(f"  Full Name: {profile.user.get_full_name()}")
            self.stdout.write(f"  Email: {profile.user.email}")
            self.stdout.write(f"  Role: {profile.role}")
            self.stdout.write(f"  Groups: {groups}")
            self.stdout.write(f"  Department: {profile.department or 'N/A'}")
            self.stdout.write(f"  License: {profile.license_number or 'N/A'}")
            self.stdout.write(f"  Is Superuser: {profile.user.is_superuser}")
            self.stdout.write(f"  Is Staff: {profile.user.is_staff}")

            # Check what this user should be able to access
            access_rights = []
            if profile.role == "admin":
                access_rights.extend(
                    [
                        "✓ Can manage all users",
                        "✓ Can view all profiles",
                        "✓ Can create/delete users",
                        "✓ Full admin access",
                    ]
                )
            elif profile.role in ["doctor", "nurse", "pharmacy"]:
                access_rights.extend(
                    [
                        "✓ Can view own profile only",
                        "✗ Cannot create users",
                        "✗ Cannot access user management",
                        "✓ Can edit own profile",
                    ]
                )
            elif profile.role == "patient":
                access_rights.extend(
                    [
                        "✓ Can view own profile only",
                        "✗ Cannot create users",
                        "✗ Cannot access user management",
                        "✓ Can edit own profile",
                    ]
                )

            self.stdout.write("  Expected Access:")
            for right in access_rights:
                color = self.style.SUCCESS if "✓" in right else self.style.ERROR
                self.stdout.write(f"    {color(right)}")

        self.stdout.write(f"\n{self.style.SUCCESS('Report completed.')}")
        self.stdout.write(
            f"{self.style.WARNING('Note: Only admin users should be able to access User management in Django admin.')}"
        )
