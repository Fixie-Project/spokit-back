from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("post", "0003_submissionbuilddetail"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Submission",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("submitter_name", models.CharField(max_length=100)),
                        ("submitter_email", models.EmailField(max_length=254)),
                        ("sns_links", models.JSONField(blank=True, default=list)),
                        ("message", models.TextField()),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("submitted", "접수됨"),
                                    ("in_review", "대기중"),
                                    ("in_progress", "포스팅중"),
                                    ("published", "포스팅 완료"),
                                    ("rejected", "반려"),
                                ],
                                default="submitted",
                                max_length=20,
                            ),
                        ),
                        ("notes", models.TextField(blank=True)),
                        ("rejection_reason", models.TextField(blank=True)),
                        ("draft_data", models.JSONField(blank=True, default=dict)),
                        ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "result_post",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="source_submissions",
                                to="post.post",
                            ),
                        ),
                        (
                            "reviewer",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="reviewed_submissions",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="submissions",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "post_submission",
                        "ordering": ["-created_at"],
                    },
                ),
                migrations.CreateModel(
                    name="SubmissionBuildDetail",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("frame", models.CharField(blank=True, max_length=200)),
                        ("fork", models.CharField(blank=True, max_length=200)),
                        ("wheelset", models.CharField(blank=True, max_length=200)),
                        ("crank", models.CharField(blank=True, max_length=200)),
                        ("chainring", models.CharField(blank=True, max_length=200)),
                        ("cog", models.CharField(blank=True, max_length=200)),
                        ("handlebar", models.CharField(blank=True, max_length=200)),
                        ("stem", models.CharField(blank=True, max_length=200)),
                        ("saddle", models.CharField(blank=True, max_length=200)),
                        ("seatpost", models.CharField(blank=True, max_length=200)),
                        ("pedal", models.CharField(blank=True, max_length=200)),
                        ("acc", models.TextField(blank=True, db_column="others")),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "submission",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="build_detail",
                                to="submission.Submission",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "post_submissionbuilddetail",
                        "verbose_name": "소개 신청 부품 정보",
                        "verbose_name_plural": "소개 신청 부품 정보",
                    },
                ),
                migrations.AddIndex(
                    model_name="submission",
                    index=models.Index(fields=["status"], name="submission_status_idx"),
                ),
                migrations.AddIndex(
                    model_name="submission",
                    index=models.Index(fields=["submitter_email"], name="submission_email_idx"),
                ),
            ],
            database_operations=[],
        )
    ]
