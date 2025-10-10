from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0010_submission_question_version"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="submission",
            name="message",
        ),
    ]
