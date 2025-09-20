from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RenameField(
            model_name="submission",
            old_name="links",
            new_name="sns_links",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="gear_info",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="photos",
        ),
        migrations.AddField(
            model_name="submission",
            name="draft_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="submission",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="result_post",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_submissions",
                to="post.post",
            ),
        ),
        migrations.AlterField(
            model_name="submission",
            name="status",
            field=models.CharField(
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
    ]
