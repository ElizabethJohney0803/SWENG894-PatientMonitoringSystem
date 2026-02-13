from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = "Create a test nurse user to debug group assignment"

    def handle(self, *args, **options):
        # Clean up any existing test user
        if User.objects.filter(username="test_nurse").exists():
            User.objects.filter(username="test_nurse").delete()
            self.stdout.write("Deleted existing test_nurse user")

        self.stdout.write("Creating test nurse user...")

        # Create user
        user = User.objects.create_user(
            username="test_nurse",
            first_name="Test",
            last_name="Nurse",
            email="test.nurse@hospital.com",
            password="testpass123",
        )

        self.stdout.write(f"Created user: {user.username}")

        # Create profile with nurse role
        profile = UserProfile.objects.create(
            user=user,
            role="nurse",
            department="Emergency",
            license_number="RN123456",
            phone="555-0123",
        )

        self.stdout.write(f"Created profile with role: {profile.role}")

        # Check groups
        user.refresh_from_db()
        groups = list(user.groups.values_list("name", flat=True))
        self.stdout.write(f"User groups after creation: {groups}")

        # Test the __str__ method
        self.stdout.write(f"Profile string representation: {str(profile)}")

        # Test group assignment manually
        self.stdout.write("\nTesting manual group assignment...")
        profile.assign_to_group()

        user.refresh_from_db()
        groups = list(user.groups.values_list("name", flat=True))
        self.stdout.write(f"User groups after manual assignment: {groups}")

        if "Nurses" in groups:
            self.stdout.write(
                self.style.SUCCESS("✓ Group assignment working correctly")
            )
        else:
            self.stdout.write(self.style.ERROR("✗ Group assignment failed"))
