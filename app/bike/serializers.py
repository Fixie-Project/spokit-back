"""바이크 관련 직렬화 도구입니다."""
from __future__ import annotations

from rest_framework import serializers

from .models import Bike, BikeSpec


class BikeSpecSerializer(serializers.ModelSerializer):
    """자전거 부품 정보를 직렬화합니다."""

    class Meta:
        model = BikeSpec
        fields = [
            "frame",
            "fork",
            "wheelset",
            "crank",
            "chainring",
            "cog",
            "handlebar",
            "stem",
            "saddle",
            "seatpost",
            "pedal",
            "acc",
        ]


class BikeSerializer(serializers.ModelSerializer):
    """자전거 기본 정보와 부품을 함께 제공합니다."""

    spec = BikeSpecSerializer(required=False)

    class Meta:
        model = Bike
        fields = [
            "id",
            "owner",
            "name",
            "is_primary",
            "created_at",
            "updated_at",
            "spec",
        ]
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def update(self, instance: Bike, validated_data: dict):
        spec_data = validated_data.pop("spec", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if spec_data is not None:
            spec, _ = BikeSpec.objects.get_or_create(bike=instance)
            for field, value in spec_data.items():
                setattr(spec, field, value)
            spec.save()

        return instance

    def create(self, validated_data: dict):
        spec_data = validated_data.pop("spec", None)
        bike = Bike.objects.create(**validated_data)
        if spec_data:
            BikeSpec.objects.create(bike=bike, **spec_data)
        return bike
