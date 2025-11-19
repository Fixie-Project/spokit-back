from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0003_post_view_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="story_snapshot",
            field=models.JSONField(default=list),
        ),
    ]
