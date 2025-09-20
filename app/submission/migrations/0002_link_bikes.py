from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    SubmissionBuildDetail = apps.get_model("submission", "SubmissionBuildDetail")
    Bike = apps.get_model("bike", "Bike")
    BikeSpec = apps.get_model("bike", "BikeSpec")
    User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])

    for submission in Submission.objects.all():
        owner = User.objects.filter(pk=submission.user_id).first() if submission.user_id else None
        base_name = submission.submitter_name or f"Submission {submission.pk}"
        name = base_name
        counter = 1
        if owner:
            exists = Bike.objects.filter(owner=owner, name=name).exists()
            while exists:
                counter += 1
                name = f"{base_name} #{counter}"
                exists = Bike.objects.filter(owner=owner, name=name).exists()
        else:
            exists = Bike.objects.filter(owner__isnull=True, name=name).exists()
            while exists:
                counter += 1
                name = f"{base_name} #{counter}"
                exists = Bike.objects.filter(owner__isnull=True, name=name).exists()
        bike = Bike.objects.create(
            owner=owner,
            name=name,
            nickname="",
            description=(submission.message or "")[:500],
            is_primary=False,
        )

        spec_data = {}
        try:
            detail = SubmissionBuildDetail.objects.get(submission_id=submission.pk)
        except SubmissionBuildDetail.DoesNotExist:
            detail = None
        if detail:
            spec_data = {
                "frame": detail.frame,
                "fork": detail.fork,
                "wheelset": detail.wheelset,
                "crank": detail.crank,
                "chainring": detail.chainring,
                "cog": detail.cog,
                "handlebar": detail.handlebar,
                "stem": detail.stem,
                "saddle": detail.saddle,
                "seatpost": detail.seatpost,
                "pedal": detail.pedal,
                "acc": detail.acc,
            }
            spec_data = {key: value for key, value in spec_data.items() if value}
        BikeSpec.objects.create(bike=bike, **spec_data)
        submission.bike = bike
        submission.save(update_fields=["bike"])


def backwards(apps, schema_editor):
    Submission = apps.get_model("submission", "Submission")
    Bike = apps.get_model("bike", "Bike")
    BikeSpec = apps.get_model("bike", "BikeSpec")

    for submission in Submission.objects.all():
        if submission.bike_id:
            spec_qs = BikeSpec.objects.filter(bike_id=submission.bike_id)
            spec_qs.delete()
            Bike.objects.filter(pk=submission.bike_id).delete()
            submission.bike_id = None
            submission.save(update_fields=["bike_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("bike", "0001_initial"),
        ("submission", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="bike",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submissions",
                to="bike.bike",
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.DeleteModel(name="SubmissionBuildDetail"),
    ]
