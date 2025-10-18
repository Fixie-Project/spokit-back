"""새 스키마에 맞춘 자전거 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from .models import Bike, BikeBuild


class BikeBuildSerializer(serializers.ModelSerializer):
    """자전거 빌드 메타데이터를 직렬화."""

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "base_bike",
            "title",
            "components",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "base_bike", "created_at", "updated_at")


class BikeSerializer(serializers.ModelSerializer):
    """자전거 기본 정보와 연결된 빌드를 함께 직렬화."""

    builds = BikeBuildSerializer(many=True, read_only=True)

    class Meta:
        model = Bike
        fields = [
            "id",
            "owner",
            "name",
            "frame_name",
            "frame_brand",
            "frame_type",
            "main_image",
            "is_public",
            "is_posted",
            "created_at",
            "updated_at",
            "builds",
        ]
        read_only_fields = ("id", "owner", "created_at", "updated_at", "builds")
