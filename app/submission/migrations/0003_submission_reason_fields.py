from django.db import migrations, models


def forward_populate_reason_fields(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    for submission in Submission.objects.exclude(rejection_reason=""):
        submission.reason_code = "other"
        submission.reason_detail = submission.rejection_reason
        submission.save(update_fields=["reason_code", "reason_detail"])


def backward_populate_rejection_reason(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    for submission in Submission.objects.exclude(reason_detail=""):
        submission.rejection_reason = submission.reason_detail
        submission.save(update_fields=["rejection_reason"])


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="reason_code",
            field=models.CharField(blank=True, choices=[
                ("content_incomplete", "콘텐츠 보완 필요"),
                ("photo_issue", "이미지 품질 문제"),
                ("guideline_mismatch", "가이드라인 불일치"),
                ("duplicate", "중복 신청"),
                ("other", "기타"),
            ], max_length=40),
        ),
        migrations.AddField(
            model_name="submission",
            name="reason_detail",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(forward_populate_reason_fields, backward_populate_rejection_reason),
        migrations.RemoveField(
            model_name="submission",
            name="rejection_reason",
        ),
    ]
