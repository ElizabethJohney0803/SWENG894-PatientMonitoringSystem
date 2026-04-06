# Generated manually for PBI-S3-04 — Automatic Allergy Conflict Detection

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="medication",
            name="allergy_conflict",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Automatically set to True when the medication name matches an entry "
                    "in the patient's recorded allergies — FR-Ph-4"
                ),
            ),
        ),
    ]
