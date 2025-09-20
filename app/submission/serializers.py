"""소개 신청 API 직렬화 도구입니다."""
from __future__ import annotations

from rest_framework import serializers

from app.bike.models import Bike
from app.bike.serializers import BikeSerializer

from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    """소개 신청과 관련된 정보를 직렬화합니다."""

    bike = BikeSerializer(required=False)
    sns_links = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Submission
        fields = [
            "id",
            "user",
            "submitter_name",
            "submitter_email",
            "sns_links",
            "message",
            "status",
            "notes",
            "rejection_reason",
            "draft_data",
            "reviewed_at",
            "reviewer",
            "result_post",
            "created_at",
            "bike",
        ]
        read_only_fields = (
            "id",
            "status",
            "notes",
            "rejection_reason",
            "draft_data",
            "reviewed_at",
            "reviewer",
            "result_post",
            "created_at",
            "user",
        )

    def create(self, validated_data: dict):
        bike_data = validated_data.pop("bike", None)
        submission = Submission.objects.create(**validated_data)
        if bike_data:
            bike_serializer = BikeSerializer(data=bike_data)
            bike_serializer.is_valid(raise_exception=True)
            bike = bike_serializer.save(owner=submission.user)
            submission.bike = bike
            submission.save(update_fields=["bike"])
        return submission

    def update(self, instance: Submission, validated_data: dict):
        bike_data = validated_data.pop("bike", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if bike_data is not None:
            if instance.bike:
                bike_serializer = BikeSerializer(instance=instance.bike, data=bike_data, partial=True)
                bike_serializer.is_valid(raise_exception=True)
                bike_serializer.save()
            else:
                bike_serializer = BikeSerializer(data=bike_data)
                bike_serializer.is_valid(raise_exception=True)
                bike = bike_serializer.save(owner=instance.user)
                instance.bike = bike
                instance.save(update_fields=["bike"])
        return instance
