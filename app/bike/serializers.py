"""새 스키마에 맞춘 자전거 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from app.core.models import BaseImage

from .models import Bike, BikeBuild, BuildImage


COMPONENT_CATEGORIES = (
    "frame_setup",
    "wheel",
    "cockpit",
    "drivetrain",
    "seat",
    "brake",
    "etc",
)

class BikeOwnerPublicSerializer(serializers.Serializer):
    """공개 목록에서 노출되는 자전거 소유자 요약."""

    id = serializers.UUIDField()
    nickname = serializers.CharField()
    username = serializers.CharField()

    @classmethod
    def from_user(cls, user):
        if not user:
            return None
        return {"id": user.id, "nickname": user.nickname, "username": user.username}


class BikeSummarySerializer(serializers.ModelSerializer):
    """자전거 요약 정보를 제공."""

    class Meta:
        model = Bike
        fields = ["id", "frame_name"]
        read_only_fields = fields


class BikeBuildSerializer(serializers.ModelSerializer):
    """자전거 빌드 메타데이터를 직렬화."""

    base_bike = BikeSummarySerializer(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = BikeBuild
        fields = [
            "id",
            "owner",
            "base_bike",
            "title",
            "is_public",
            "created_at",
            "updated_at",
            "main_image_url",
            "like_count",
            "is_liked",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_main_image_url(self, obj: BikeBuild):
        image = getattr(obj, "main_image", None)
        if not image:
            return None
        return image.url

    def get_owner(self, obj: BikeBuild):
        bike = getattr(obj, "base_bike", None)
        return BikeOwnerPublicSerializer.from_user(getattr(bike, "owner", None))

    def get_is_liked(self, obj: BikeBuild) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        prefetched_likes = (
            obj._prefetched_objects_cache.get("likes")
            if hasattr(obj, "_prefetched_objects_cache")
            else None
        )
        if prefetched_likes is not None:
            return any(like.user_id == user.id for like in prefetched_likes)
        return obj.likes.filter(user=user).exists()


class BikeBuildWriteSerializer(serializers.ModelSerializer):
    """자전거 빌드를 생성/수정하는 직렬화기."""

    main_image = serializers.PrimaryKeyRelatedField(
        queryset=BaseImage.objects.all(), required=False, allow_null=True
    )
    images = serializers.PrimaryKeyRelatedField(
        queryset=BaseImage.objects.all(), many=True, required=False, allow_empty=True, write_only=True
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
            "images",
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

    def _set_images(self, build: BikeBuild, images: list[BaseImage]):
        if images is None:
            return
        BuildImage.objects.filter(build=build).delete()
        BuildImage.objects.bulk_create(
            [BuildImage(build=build, image=image, order=idx) for idx, image in enumerate(images)]
        )

    def validate_images(self, value):
        if value is None:
            return value
        if len(value) > 9:
            raise serializers.ValidationError("이미지는 최대 9장까지 등록할 수 있습니다.")
        return value

    def create(self, validated_data):
        images = validated_data.pop("images", None)
        build = super().create(validated_data)
        if images is not None:
            self._set_images(build, images)
        return build

    def update(self, instance: BikeBuild, validated_data):
        images = validated_data.pop("images", None)
        if "base_bike" in validated_data:
            raise serializers.ValidationError(
                {"base_bike": "기존 빌드의 프레임은 변경할 수 없습니다. 새 빌드를 생성해 주세요."}
            )
        build = super().update(instance, validated_data)
        if images is not None:
            self._set_images(build, images)
        return build


class BikeSerializer(serializers.ModelSerializer):
    """자전거 기본 정보와 연결된 빌드를 함께 직렬화."""

    builds = BikeBuildSerializer(many=True, read_only=True)
    main_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Bike
        fields = [
            "id",
            "owner",
            "name",
            "frame_name",
            "main_image_url",
            "is_posted",
            "created_at",
            "updated_at",
            "builds",
        ]
        read_only_fields = ("id", "owner", "created_at", "updated_at", "builds")

    def get_main_image_url(self, obj: Bike):
        image = getattr(obj, "main_image", None)
        if not image:
            return None
        return image.url


class BikeBuildDetailSerializer(serializers.ModelSerializer):
    """자전거 빌드의 상세 정보를 직렬화."""

    base_bike = BikeSummarySerializer(read_only=True)
    main_image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    is_liked = serializers.SerializerMethodField()

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
            "main_image",
            "images",
            "like_count",
            "is_liked",
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

    def get_images(self, obj: BikeBuild):
        gallery = getattr(obj, "images", None)
        if not gallery:
            return []
        return [
            {
                "id": str(item.image_id),
                "url": item.image.url,
                "width": item.image.width,
                "height": item.image.height,
                "order": item.order,
                "caption": item.caption,
            }
            for item in gallery.all()
        ]

    def get_is_liked(self, obj: BikeBuild) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        prefetched_likes = (
            obj._prefetched_objects_cache.get("likes")
            if hasattr(obj, "_prefetched_objects_cache")
            else None
        )
        if prefetched_likes is not None:
            return any(like.user_id == user.id for like in prefetched_likes)
        return obj.likes.filter(user=user).exists()


class MessageSerializer(serializers.Serializer):
    """응답 메시지 기본 형태."""

    message = serializers.CharField()


class BikeListResponseSerializer(MessageSerializer):
    data = BikeSerializer(many=True)


class BikeDetailResponseSerializer(MessageSerializer):
    data = BikeSerializer()

class BikeBuildListResponseSerializer(MessageSerializer):
    data = BikeBuildSerializer(many=True)


class BikeBuildDetailResponseSerializer(MessageSerializer):
    data = BikeBuildDetailSerializer()


class BikeBuildArchiveDataSerializer(serializers.Serializer):
    """공개 아카이브 목록 응답 데이터."""

    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = BikeBuildSerializer(many=True)


class BikeBuildArchiveResponseSerializer(MessageSerializer):
    """공개 아카이브 응답 래퍼."""

    data = BikeBuildArchiveDataSerializer()


class BikeBuildLikeToggleResponseSerializer(MessageSerializer):
    """빌드 좋아요 토글 응답 래퍼."""

    data = serializers.DictField()
