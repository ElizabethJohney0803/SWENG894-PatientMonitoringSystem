from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_medication_risk_level_medication_risk_score_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="medication",
            name="risk_level",
        ),
        migrations.RemoveField(
            model_name="medication",
            name="risk_score",
        ),
    ]
