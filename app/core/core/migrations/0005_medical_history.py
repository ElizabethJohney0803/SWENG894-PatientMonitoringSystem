# Migration: medical history fields on Patient + Medication model (PMS-014)
# Generated for Sprint 4 medical history feature.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_testresult"),
    ]

    operations = [
        # ── Add medical history fields to Patient ──────────────────────
        migrations.AddField(
            model_name="patient",
            name="diagnoses",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Current and past diagnoses — editable by Doctor/Admin, "
                    "read-only for Nurse, hidden from Patient"
                ),
            ),
        ),
        migrations.AddField(
            model_name="patient",
            name="procedures",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Surgical and clinical procedures performed — "
                    "read-only for Nurse, hidden from Patient"
                ),
            ),
        ),
        migrations.AddField(
            model_name="patient",
            name="visit_notes",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Prior visit notes and clinical observations — "
                    "read-only for Nurse, hidden from Patient"
                ),
            ),
        ),
        migrations.AddField(
            model_name="patient",
            name="allergies",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Known allergies — visible to Doctor/Nurse/Pharmacy/Admin, "
                    "hidden from Patient — FR-Ph-3"
                ),
            ),
        ),
        migrations.AddField(
            model_name="patient",
            name="chronic_conditions",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Long-term chronic conditions — "
                    "read-only for Nurse, hidden from Patient"
                ),
            ),
        ),
        # ── Create Medication model ────────────────────────────────────
        migrations.CreateModel(
            name="Medication",
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
                    "medication_name",
                    models.CharField(
                        help_text=("Name of the medication (e.g. Metformin)"),
                        max_length=200,
                    ),
                ),
                (
                    "dosage",
                    models.CharField(
                        help_text="Dosage (e.g. 500 mg)",
                        max_length=100,
                    ),
                ),
                (
                    "frequency",
                    models.CharField(
                        help_text="Frequency (e.g. Twice daily)",
                        max_length=100,
                    ),
                ),
                (
                    "start_date",
                    models.DateField(help_text="Date the medication was started"),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        help_text=(
                            "Date the medication was stopped " "(blank = ongoing)"
                        ),
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("current", "Current"),
                            ("past", "Past"),
                        ],
                        default="current",
                        help_text=("Whether the medication is currently active"),
                        max_length=10,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Additional notes or instructions",
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
                    "patient",
                    models.ForeignKey(
                        help_text=("Patient this medication belongs to"),
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medications",
                        to="core.patient",
                    ),
                ),
                (
                    "prescribing_doctor",
                    models.ForeignKey(
                        blank=True,
                        help_text="Doctor who prescribed this medication",
                        limit_choices_to={"role": "doctor"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="prescribed_medications",
                        to="core.userprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Medication",
                "verbose_name_plural": "Medications",
                "ordering": ["status", "-start_date"],
            },
        ),
    ]
