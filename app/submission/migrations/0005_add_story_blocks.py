from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0004_submission_remove_submitter_fields_add_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="story_blocks",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="submission",
            name="blocks_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="submission",
            name="message",
            field=models.TextField(blank=True),
        ),
    ]
