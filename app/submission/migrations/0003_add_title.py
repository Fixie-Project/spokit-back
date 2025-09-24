from django.db import migrations, models


def forwards(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    for submission in Submission.objects.all():
        if not submission.title:
            submission.title = submission.submitter_name or (submission.message[:50] if submission.message else "")
            submission.save(update_fields=["title"])


def backwards(apps, schema_editor):
    # Nothing to revert; retaining title data
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0002_link_bikes"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="title",
            field=models.CharField(default="", max_length=200),
        ),
        migrations.RunPython(forwards, backwards),
    ]
