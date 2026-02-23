# Generated migration for Patient-Doctor assignment feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_patient_emergencycontact"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="assigned_doctor",
            field=models.ForeignKey(
                blank=True,
                help_text="Doctor assigned to this patient (admin-only assignment)",
                limit_choices_to={"role": "doctor"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_patients",
                to="core.userprofile",
            ),
        ),
    ]
