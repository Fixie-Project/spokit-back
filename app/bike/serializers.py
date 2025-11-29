"""새 스키마에 맞춘 자전거 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from app.core.models import BaseImage

from .models import Bike, BikeBuild


COMPONENT_CATEGORIES = (
    "frame_setup",
    "wheel",
    "cockpit",
    "drivetrain",
    "seat",
    "brake",
    "etc",
)

class BikePublicListSerializer(serializers.ModelSerializer):
    """공개 목록에서 사용하는 자전거 요약."""

    build_names = serializers.SerializerMethodField()

    class Meta:
        model = Bike
        fields = [
            "id",
            "name",
            "frame_name",
            "created_at",
            "updated_at",
            "build_names",
        ]
        read_only_fields = fields

    def get_build_names(self, obj: Bike) -> list[str]:
        builds = getattr(obj, "_public_builds", None)
        if builds is None:
            builds = [build for build in obj.builds.all() if build.is_public]
        return [build.title for build in builds]


class BikeSummarySerializer(serializers.ModelSerializer):
    """자전거 요약 정보를 제공."""

    class Meta:
        model = Bike
        fields = ["id", "frame_name"]
        read_only_fields = fields


class BikeBuildSerializer(serializers.ModelSerializer):
    """자전거 빌드 메타데이터를 직렬화."""

    base_bike = BikeSummarySerializer(read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "base_bike",
            "title",
            "is_public",
            "created_at",
            "updated_at",
            "main_image",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_main_image(self, obj: BikeBuild):
        image = getattr(obj, "main_image", None)
        if not image:
            return None
        return {
            "url": image.url,
            "width": image.width,
            "height": image.height,
        }


class BikeBuildWriteSerializer(serializers.ModelSerializer):
    """자전거 빌드를 생성/수정하는 직렬화기."""

    main_image = serializers.PrimaryKeyRelatedField(
        queryset=BaseImage.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "base_bike",
            "title",
            "components",
            "note",
            "is_public",
            "main_image",
        ]
        read_only_fields = ("id",)
        extra_kwargs = {
            "components": {
                "help_text": "카테고리별 부품 리스트. 예: {\"wheel\": [\"Phil Wood hub\", \"H Plus Son rim\"]}"
            }
        }

    def validate_components(self, value):
        if value in (None, "", []):
            raise serializers.ValidationError("components 필드를 입력해 주세요.")
        if not isinstance(value, dict):
            raise serializers.ValidationError("components 필드는 객체 형태여야 합니다.")

        cleaned: dict[str, list[str]] = {}
        for category, items in value.items():
            if category not in COMPONENT_CATEGORIES:
                raise serializers.ValidationError({category: "허용되지 않은 카테고리입니다."})

            if isinstance(items, str):
                items_list = [items]
            elif isinstance(items, list):
                items_list = items
            else:
                raise serializers.ValidationError({category: "리스트 또는 문자열만 허용됩니다."})

            normalized: list[str] = []
            for item in items_list:
                if item in (None, ""):
                    continue
                if not isinstance(item, str):
                    raise serializers.ValidationError({category: "항목은 문자열이어야 합니다."})
                text = item.strip()
                if text:
                    normalized.append(text)

            if normalized:
                cleaned[category] = normalized

        if len(cleaned) < 3:
            raise serializers.ValidationError("최소 3개 이상의 카테고리를 입력해 주세요.")

        return cleaned


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


class MessageSerializer(serializers.Serializer):
    """응답 메시지 기본 형태."""

    message = serializers.CharField()


class BikeListResponseSerializer(MessageSerializer):
    data = BikeSerializer(many=True)


class BikeDetailResponseSerializer(MessageSerializer):
    data = BikeSerializer()


class BikePublicListResponseSerializer(MessageSerializer):
    data = BikePublicListSerializer(many=True)


class BikeBuildListResponseSerializer(MessageSerializer):
    data = BikeBuildSerializer(many=True)


class BikeBuildDetailResponseSerializer(MessageSerializer):
    data = BikeBuildDetailSerializer()
