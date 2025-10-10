from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0008_move_notes_to_studio"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="question_version",
            field=models.CharField(default="v1_3", max_length=20),
        ),
    ]
