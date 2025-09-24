from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bike", "0002_remove_bike_nickname"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bike",
            name="description",
        ),
    ]
