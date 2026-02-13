"""
Test runner script and utilities for the Patient Monitoring System.
"""

import pytest
import os
import sys
from django.conf import settings
from django.core.management import execute_from_command_line


def run_all_tests():
    """Run all tests with comprehensive reporting."""
    print("=" * 60)
    print("PATIENT MONITORING SYSTEM - TEST SUITE")
    print("=" * 60)

    # Test commands for different test categories
    test_commands = {
        "Unit Tests - Models": [
            "python",
            "-m",
            "pytest",
            "tests/test_models.py",
            "-v",
            "-m",
            "unit",
        ],
        "Unit Tests - Forms": [
            "python",
            "-m",
            "pytest",
            "tests/test_forms.py",
            "-v",
            "-m",
            "unit",
        ],
        "Unit Tests - Permissions": [
            "python",
            "-m",
            "pytest",
            "tests/test_permissions.py",
            "-v",
            "-m",
            "unit",
        ],
        "Integration Tests": [
            "python",
            "-m",
            "pytest",
            "tests/test_integration.py",
            "-v",
            "-m",
            "integration",
        ],
        "System Tests": [
            "python",
            "-m",
            "pytest",
            "tests/test_integration.py",
            "-v",
            "-m",
            "system",
        ],
        "All Tests": ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
    }

    return test_commands


def run_coverage_report():
    """Run tests with coverage reporting."""
    return [
        "python",
        "-m",
        "pytest",
        "--cov=core",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80",
        "tests/",
    ]


def run_specific_markers():
    """Run tests by specific markers."""
    markers = {
        "models": "Tests for Django models",
        "forms": "Tests for Django forms",
        "permissions": "Tests for permission system",
        "admin": "Tests for admin interface",
        "integration": "Integration tests",
        "system": "System/end-to-end tests",
    }

    print("\nAvailable test markers:")
    for marker, description in markers.items():
        print(f"  {marker:12} - {description}")

    return markers


if __name__ == "__main__":
    # Set up Django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pms.settings")

    import django

    django.setup()

    # Display available test commands
    commands = run_all_tests()
    markers = run_specific_markers()

    print(f"\nTo run specific test categories:")
    print(f"  pytest tests/test_models.py -m models")
    print(f"  pytest tests/test_forms.py -m forms")
    print(f"  pytest tests/test_permissions.py -m permissions")
    print(f"  pytest tests/test_integration.py -m integration")
    print(f"  pytest tests/test_integration.py -m system")

    print(f"\nTo run with coverage:")
    coverage_cmd = run_coverage_report()
    print(f"  {' '.join(coverage_cmd)}")

    print(f"\nTo run all tests:")
    print(f"  pytest tests/ -v")

    print("\n" + "=" * 60)
