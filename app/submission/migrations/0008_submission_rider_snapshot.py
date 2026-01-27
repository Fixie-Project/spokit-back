"""Add rider_snapshot to Submission."""
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0003_submission_reason_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="rider_snapshot",
            field=models.JSONField(default=dict),
        ),
    ]
