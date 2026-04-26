from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_remove_medication_risk_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="medication",
            name="risk_level",
            field=models.CharField(
                choices=[
                    ("critical", "Critical"),
                    ("high", "High"),
                    ("medium", "Medium"),
                    ("safe", "Safe"),
                ],
                default="safe",
                help_text="Drug-allergy risk classification from the DrugAllergyRiskEngine — PBI-S4-17",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="medication",
            name="risk_score",
            field=models.IntegerField(
                default=0,
                help_text="Numeric risk score: 100=critical, 75=high, 50=medium, 0=safe — PBI-S4-17",
            ),
        ),
    ]
