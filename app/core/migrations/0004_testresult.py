# Migration: create TestResult model (PMS-013)
# Generated for Sprint 4 test results feature.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_add_patient_doctor_assignment"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "test_name",
                    models.CharField(
                        help_text=("Name of the test (e.g. Complete Blood Count)"),
                        max_length=200,
                    ),
                ),
                (
                    "test_type",
                    models.CharField(
                        choices=[
                            ("blood_panel", "Blood Panel"),
                            ("metabolic_panel", "Metabolic Panel"),
                            ("urinalysis", "Urinalysis"),
                            ("hormone_panel", "Hormone Panel"),
                            ("lipid_panel", "Lipid Panel"),
                            ("imaging", "Imaging"),
                            ("other", "Other"),
                        ],
                        default="other",
                        help_text="Category of the test",
                        max_length=20,
                    ),
                ),
                (
                    "test_date",
                    models.DateField(help_text="Date the test was performed"),
                ),
                (
                    "result_value",
                    models.CharField(
                        help_text=("Result value " "(e.g. '7.2', 'Negative', '14.5')"),
                        max_length=100,
                    ),
                ),
                (
                    "result_unit",
                    models.CharField(
                        blank=True,
                        help_text=("Unit of measurement (e.g. g/dL, mg/dL)"),
                        max_length=50,
                    ),
                ),
                (
                    "reference_range",
                    models.CharField(
                        blank=True,
                        help_text=("Normal reference range " "(e.g. '12.0-17.5 g/dL')"),
                        max_length=100,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("normal", "Normal"),
                            ("low", "Low"),
                            ("high", "High"),
                            ("critical", "Critical"),
                            ("pending", "Pending"),
                        ],
                        default="pending",
                        help_text=("Result status relative to reference range"),
                        max_length=10,
                    ),
                ),
                (
                    "doctor_notes",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Doctor's notes and interpretation of the " "results"
                        ),
                    ),
                ),
                (
                    "follow_up_required",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Indicates whether a follow-up appointment " "is required"
                        ),
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "ordering_doctor",
                    models.ForeignKey(
                        blank=True,
                        help_text="Doctor who ordered this test",
                        limit_choices_to={"role": "doctor"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ordered_tests",
                        to="core.userprofile",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        help_text=("Patient this test result belongs to"),
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_results",
                        to="core.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "Test Result",
                "verbose_name_plural": "Test Results",
                "ordering": ["-test_date", "-created_at"],
            },
        ),
    ]
