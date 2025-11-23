from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0004_post_story_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="is_editor_pick",
            field=models.BooleanField(default=False),
        ),
    ]
