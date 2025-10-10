from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("post", "0001_initial"),
        ("submission", "0007_submission_external_story_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionReviewNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("post_status", models.CharField(blank=True, choices=[("draft", "초안"), ("review", "검수중"), ("published", "게시됨")], max_length=20)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="submission_review_notes", to=settings.AUTH_USER_MODEL)),
                ("post", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="submission_review_notes", to="post.post")),
                ("submission", models.ForeignKey(on_delete=models.CASCADE, related_name="review_notes", to="submission.submission")),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "신청서 검토 메모",
                "verbose_name_plural": "신청서 검토 메모",
            },
        ),
    ]
