from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_medication_allergy_conflict"),
    ]

    operations = [
        migrations.AddField(
            model_name="medication",
            name="fulfillment_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("dispensed", "Dispensed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                help_text="Prescription fulfillment lifecycle status — FR-D-5 / FR-Ph-1",
                max_length=15,
            ),
        ),
    ]
