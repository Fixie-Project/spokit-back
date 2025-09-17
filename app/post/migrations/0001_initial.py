# Generated manually to define core post models.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitter_name", models.CharField(max_length=100)),
                ("submitter_email", models.EmailField(max_length=254)),
                ("links", models.JSONField(blank=True, default=list)),
                ("photos", models.JSONField(blank=True, default=list)),
                ("gear_info", models.JSONField(blank=True, default=dict)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("pending", "대기"), ("approved", "승인"), ("rejected", "반려")], default="pending", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reviewer",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_submissions", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("summary", models.TextField(blank=True)),
                ("body", models.TextField(help_text="마크다운 또는 HTML로 자유롭게 작성")),
                ("cover_image", models.URLField(blank=True)),
                ("spec", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("draft", "초안"), ("review", "검수중"), ("published", "게시됨")], default="draft", max_length=20)),
                ("featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "tags",
                    models.ManyToManyField(blank=True, related_name="posts", to="post.tag"),
                ),
            ],
            options={
                "ordering": ["-published_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Like",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="post.post"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("is_blocked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="post.post"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="like",
            constraint=models.UniqueConstraint(fields=("post", "user"), name="post_like_unique"),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["slug"], name="post_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["status", "published_at"], name="post_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["slug"], name="tag_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(fields=["status"], name="submission_status_idx"),
        ),
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(fields=["submitter_email"], name="submission_email_idx"),
        ),
    ]
