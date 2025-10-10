from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0006_submission_required_question_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="external_story_url",
            field=models.URLField(blank=True),
        ),
    ]
