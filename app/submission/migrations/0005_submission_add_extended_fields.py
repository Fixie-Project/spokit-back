from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0004_submission_remove_submitter_fields_add_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="display_name",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="location",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="category",
            field=models.CharField(blank=True, choices=[("track", "트랙"), ("street", "스트리트"), ("messenger", "메신저"), ("vintage", "빈티지"), ("custom", "커스텀"), ("other", "기타")], default="", max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="story_summary",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="story_inspiration",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="story_challenges",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="consent_portrait",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="submission",
            name="consent_license",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="submission",
            name="consent_updates",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="submission",
            name="cover_image",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="as_cover_for", to="submission.submissionimage"),
        ),
    ]
