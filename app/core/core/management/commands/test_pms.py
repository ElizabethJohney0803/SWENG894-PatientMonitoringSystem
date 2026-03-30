"""
Test commands for Patient Monitoring System
Usage: python manage.py test_pms
"""

from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = "Run Patient Monitoring System test suite"

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            choices=[
                "unit",
                "integration",
                "system",
                "all",
                "models",
                "forms",
                "permissions",
                "admin",
            ],
            default="all",
            help="Test category to run",
        )
        parser.add_argument(
            "--coverage", action="store_true", help="Run tests with coverage report"
        )
        parser.add_argument("--verbose", action="store_true", help="Verbose output")

    def handle(self, *args, **options):
        category = options["category"]
        coverage = options["coverage"]
        verbose = options["verbose"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Running {category} tests for Patient Monitoring System"
            )
        )

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        if coverage:
            cmd.extend(["--cov=core", "--cov-report=html", "--cov-report=term-missing"])

        if verbose:
            cmd.append("-v")

        # Add test path based on category
        if category == "all":
            cmd.append("tests/")
        elif category == "unit":
            cmd.extend(["tests/", "-m", "unit"])
        elif category == "integration":
            cmd.extend(["tests/test_integration.py", "-m", "integration"])
        elif category == "system":
            cmd.extend(["tests/test_integration.py", "-m", "system"])
        elif category == "models":
            cmd.extend(["tests/test_models.py", "-m", "models"])
        elif category == "forms":
            cmd.extend(["tests/test_forms.py", "-m", "forms"])
        elif category == "permissions":
            cmd.extend(["tests/test_permissions.py", "-m", "permissions"])
        elif category == "admin":
            cmd.extend(["tests/", "-m", "admin"])

        # Run tests
        try:
            result = subprocess.run(cmd, cwd="/app", capture_output=False)
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS("✅ All tests passed!"))
            else:
                self.stdout.write(self.style.ERROR("❌ Some tests failed!"))
                sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running tests: {e}"))
            sys.exit(1)
