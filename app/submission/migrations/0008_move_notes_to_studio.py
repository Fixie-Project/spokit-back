from django.db import migrations


def move_notes_to_studio(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    ReviewNote = apps.get_model("studio", "SubmissionReviewNote")

    submissions = Submission.objects.exclude(notes__isnull=True).exclude(notes="")
    for submission in submissions.iterator():
        note = ReviewNote.objects.create(
            submission=submission,
            author=getattr(submission, "reviewer", None),
            post=getattr(submission, "result_post", None),
            post_status=submission.result_post.status if submission.result_post_id else "",
            note=submission.notes,
        )
        if submission.reviewed_at:
            ReviewNote.objects.filter(pk=note.pk).update(
                created_at=submission.reviewed_at,
                updated_at=submission.reviewed_at,
            )


def noop_reverse(apps, schema_editor):
    # 역이동은 지원하지 않습니다.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0001_submission_review_note"),
        ("submission", "0007_submission_external_story_url"),
    ]

    operations = [
        migrations.RunPython(move_notes_to_studio, reverse_code=noop_reverse),
        migrations.RemoveField(
            model_name="submission",
            name="notes",
        ),
    ]
