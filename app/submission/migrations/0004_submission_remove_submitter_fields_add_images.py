from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0003_add_title"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="submission",
            options={
                "db_table": "post_submission",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["status"], name="submission_status_idx")],
            },
        ),
        migrations.RemoveField(
            model_name="submission",
            name="submitter_email",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="submitter_name",
        ),
        migrations.CreateModel(
            name="SubmissionImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="submission_images/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="images", to="submission.submission"),
                ),
            ],
            options={
                "ordering": ["created_at", "pk"],
                "db_table": "post_submission_image",
            },
        ),
    ]
