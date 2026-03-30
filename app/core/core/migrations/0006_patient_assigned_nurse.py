import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_medical_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="assigned_nurse",
            field=models.ForeignKey(
                blank=True,
                help_text=("Nurse assigned to this patient " "(admin-only assignment)"),
                limit_choices_to={"role": "nurse"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_nurse_patients",
                to="core.userprofile",
            ),
        ),
    ]
