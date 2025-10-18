"""새 스키마에 맞춘 자전거 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from .models import Bike, BikeBuild


class BikePublicListSerializer(serializers.ModelSerializer):
    """공개 목록에서 사용하는 자전거 요약."""

    class Meta:
        model = Bike
        fields = ["id", "name", "frame_name", "frame_brand", "frame_type", "created_at", "updated_at"]
        read_only_fields = fields


class BikeSummarySerializer(serializers.ModelSerializer):
    """자전거 요약 정보를 제공."""

    class Meta:
        model = Bike
        fields = ["id", "frame_name", "frame_brand", "frame_type"]
        read_only_fields = fields


class BikeBuildSerializer(serializers.ModelSerializer):
    """자전거 빌드 메타데이터를 직렬화."""

    base_bike = BikeSummarySerializer(read_only=True)

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "base_bike",
            "title",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class BikeBuildWriteSerializer(serializers.ModelSerializer):
    """자전거 빌드를 생성/수정하는 직렬화기."""

    class Meta:
        model = BikeBuild
        fields = ["id", "base_bike", "title", "components", "note", "is_public"]
        read_only_fields = ("id",)
        extra_kwargs = {
            "components": {
                "help_text": "카테고리별 부품 정보. 예: {\"wheel\": {\"brand\": \"H Plus Son\", \"model\": \"AT-25\", \"details\": {\"hub\": {\"brand\": \"Phil Wood\", \"model\": \"Low Flange\"}}}}"
            }
        }

    def validate_components(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("components 필드는 객체 형태여야 합니다.")
        return value


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


class BikeBuildDetailSerializer(serializers.ModelSerializer):
    """자전거 빌드의 상세 정보를 직렬화."""

    base_bike = BikeSummarySerializer(read_only=True)

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "base_bike",
            "title",
            "components",
            "note",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")
