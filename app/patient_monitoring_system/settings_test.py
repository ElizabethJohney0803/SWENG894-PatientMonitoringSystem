"""
Test-specific Django settings for Patient Monitoring System.
Uses SQLite for testing to avoid Docker PostgreSQL dependency.
"""

from .settings import *

# Override database to use SQLite for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up tests by using a simpler password hasher
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Debug should be False for testing
DEBUG = False

# Use a simple cache backend for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}


# Disable migrations for testing to speed up test database creation
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Secret key for testing
SECRET_KEY = "test-secret-key-only-for-testing"

# Test-specific security settings
ALLOWED_HOSTS = ["*"]
