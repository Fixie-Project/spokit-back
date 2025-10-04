from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bike", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bike",
            name="nickname",
        ),
    ]
