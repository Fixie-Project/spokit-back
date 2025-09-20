from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("nickname", models.CharField(blank=True, max_length=100)),
                ("description", models.TextField(blank=True)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bikes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["owner", "-is_primary", "name"],
                "unique_together": {("owner", "name")},
            },
        ),
        migrations.CreateModel(
            name="BikeSpec",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("frame", models.CharField(blank=True, max_length=200)),
                ("fork", models.CharField(blank=True, max_length=200)),
                ("wheelset", models.CharField(blank=True, max_length=200)),
                ("crank", models.CharField(blank=True, max_length=200)),
                ("chainring", models.CharField(blank=True, max_length=200)),
                ("cog", models.CharField(blank=True, max_length=200)),
                ("handlebar", models.CharField(blank=True, max_length=200)),
                ("stem", models.CharField(blank=True, max_length=200)),
                ("saddle", models.CharField(blank=True, max_length=200)),
                ("seatpost", models.CharField(blank=True, max_length=200)),
                ("pedal", models.CharField(blank=True, max_length=200)),
                ("acc", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bike",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spec",
                        to="bike.bike",
                    ),
                ),
            ],
            options={
                "verbose_name": "바이크 부품",
                "verbose_name_plural": "바이크 부품",
            },
        ),
    ]
