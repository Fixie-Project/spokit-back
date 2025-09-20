from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0002_submission_workflow_updates"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionBuildDetail",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("frame", models.CharField(blank=True, max_length=200)),
                ("fork", models.CharField(blank=True, max_length=200)),
                ("wheelset", models.CharField(blank=True, max_length=200)),
                ("tire", models.CharField(blank=True, max_length=200)),
                ("crank", models.CharField(blank=True, max_length=200)),
                ("chainring", models.CharField(blank=True, max_length=200)),
                ("cog", models.CharField(blank=True, max_length=200)),
                ("sprocket", models.CharField(blank=True, max_length=200)),
                ("handlebar", models.CharField(blank=True, max_length=200)),
                ("stem", models.CharField(blank=True, max_length=200)),
                ("saddle", models.CharField(blank=True, max_length=200)),
                ("seatpost", models.CharField(blank=True, max_length=200)),
                ("pedal", models.CharField(blank=True, max_length=200)),
                ("others", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "submission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="build_detail",
                        to="post.submission",
                    ),
                ),
            ],
            options={
                "verbose_name": "소개 신청 부품 정보",
                "verbose_name_plural": "소개 신청 부품 정보",
            },
        ),
    ]
