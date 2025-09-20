from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0003_submissionbuilddetail"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="SubmissionBuildDetail"),
                migrations.DeleteModel(name="Submission"),
            ],
        ),
    ]
