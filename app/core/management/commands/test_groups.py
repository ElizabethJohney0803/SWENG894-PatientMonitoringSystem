from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from core.models import UserProfile


class Command(BaseCommand):
    help = "Test group assignment for a specific user"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username to test")

    def handle(self, *args, **options):
        username = options["username"]

        try:
            user = User.objects.get(username=username)
            profile = user.profile

            self.stdout.write(f"Testing user: {username}")
            self.stdout.write(f"Current role: {profile.role}")
            self.stdout.write(
                f"Current groups: {list(user.groups.values_list('name', flat=True))}"
            )

            # Test group assignment
            self.stdout.write("\nTesting group assignment...")
            profile.assign_to_group()

            user.refresh_from_db()
            self.stdout.write(
                f"After assignment - Groups: {list(user.groups.values_list('name', flat=True))}"
            )

            # Show all available groups
            self.stdout.write(
                f"\nAll available groups: {list(Group.objects.values_list('name', flat=True))}"
            )

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{username}' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
