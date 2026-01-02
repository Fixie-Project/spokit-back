"""Core utility serializers."""
from __future__ import annotations

from rest_framework import serializers

from app.post.models import Post, PostStatus, PostImagePurpose
from app.user.models import User
from app.bike.models import BikeBuild
from .models import BaseImage
from rest_framework import serializers


class BaseImageUploadSerializer(serializers.ModelSerializer):
    """Simple serializer for creating BaseImage records after upload."""

    class Meta:
        model = BaseImage
        fields = ["id", "url", "s3_key", "width", "height", "filesize"]
        read_only_fields = ("id",)


class PostSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 게시글 요약."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "slug", "main_title", "sub_title", "is_editor_pick", "image"]
        read_only_fields = fields

    def get_image(self, obj: Post):
        images = getattr(obj, "_prefetched_objects_cache", {}).get("images") if hasattr(obj, "_prefetched_objects_cache") else None
        if images is None:
            return None
        # choose header > hero > thumbnail > body, then lowest order
        priority = {PostImagePurpose.HEADER: 0, PostImagePurpose.HERO: 1, PostImagePurpose.THUMBNAIL: 2, PostImagePurpose.BODY: 3}
        sorted_imgs = sorted(images, key=lambda i: (priority.get(i.purpose, 99), i.order))
        if not sorted_imgs:
            return None
        img = sorted_imgs[0]
        return {"url": img.url, "purpose": img.purpose}


class RiderSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 라이더 요약."""

    name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "intro", "profile_image"]
        read_only_fields = fields

    def get_name(self, obj: User) -> str:
        return obj.nickname or obj.username

    def get_profile_image(self, obj: User):
        image = getattr(obj, "profile_image", None)
        if not image:
            return None
        return {"url": image.url, "width": image.width, "height": image.height}


class BuildSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 빌드 요약(공개)."""

    bike_frame = serializers.CharField(source="base_bike.frame_name", read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = BikeBuild
        fields = ["id", "title", "bike_frame", "is_public", "main_image"]
        read_only_fields = fields

    def get_main_image(self, obj: BikeBuild):
        image = getattr(obj, "main_image", None)
        if not image:
            return None
        return {"url": image.url, "width": image.width, "height": image.height}


class GlobalSearchResponseSerializer(serializers.Serializer):
    """검색 응답 페이로드 구조."""

    posts = PostSearchSerializer(many=True)
    riders = RiderSearchSerializer(many=True)
    builds = BuildSearchSerializer(many=True)


class MessageSerializer(serializers.Serializer):
    """통일된 메시지 래퍼."""

    message = serializers.CharField()


class GlobalSearchMessageSerializer(MessageSerializer):
    """통합 검색 래퍼."""

    data = GlobalSearchResponseSerializer()
