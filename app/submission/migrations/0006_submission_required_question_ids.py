from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0005_add_story_blocks"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="required_question_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
