#!/usr/bin/env python
"""
Python test runner for Patient Monitoring System
Handles Django setup and runs pytest with proper configuration
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_django():
    """Configure Django before running tests"""
    # Add the app directory to Python path
    app_dir = Path(__file__).parent.absolute()
    sys.path.insert(0, str(app_dir))

    # Set Django settings
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "patient_monitoring_system.settings_test"
    )

    # Initialize Django
    import django

    django.setup()

    return app_dir


def run_tests(category="all", coverage=False, verbose=True):
    """Run tests with specified parameters"""
    app_dir = setup_django()

    print(f"🧪 Running {category.upper()} tests for Patient Monitoring System")
    print("=" * 60)

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    if coverage:
        cmd.extend(["--cov=core", "--cov-report=html", "--cov-report=term-missing"])

    if verbose:
        cmd.append("-v")

    cmd.append("--tb=short")

    # Add test path and markers based on category
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
    else:
        cmd.append("tests/")

    # Change to app directory and run tests
    original_dir = os.getcwd()
    try:
        os.chdir(app_dir)
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Patient Monitoring System tests")
    parser.add_argument(
        "--category",
        choices=[
            "all",
            "unit",
            "integration",
            "system",
            "models",
            "forms",
            "permissions",
        ],
        default="all",
        help="Test category to run",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    success = run_tests(
        category=args.category, coverage=args.coverage, verbose=not args.quiet
    )

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
