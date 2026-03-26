"""Core utility serializers."""
from __future__ import annotations

import re

from rest_framework import serializers

from app.post.models import Post, PostStatus, PostImagePurpose
from app.user.models import User
from app.bike.models import BikeBuild
from .models import BaseImage
from rest_framework import serializers


EXCERPT_DEFAULT_LENGTH = 120


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _normalize_whitespace(re.sub(r"<[^>]+>", " ", text))


def _build_word_pattern(keyword: str) -> re.Pattern[str] | None:
    tokens = [re.escape(token) for token in re.split(r"\s+", (keyword or "").strip()) if token]
    if not tokens:
        return None
    pattern = r"\b(" + "|".join(tokens) + r")\b"
    return re.compile(pattern, flags=re.IGNORECASE)


def _make_excerpt(text: str, keyword: str, max_length: int = EXCERPT_DEFAULT_LENGTH) -> str | None:
    if not text or not keyword:
        return None
    pattern = _build_word_pattern(keyword)
    if not pattern:
        return None
    match = pattern.search(text)
    if not match:
        return None
    start = max(0, match.start() - max_length // 2)
    end = min(len(text), start + max_length)
    snippet = text[start:end].strip()
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


class BaseImageUploadSerializer(serializers.ModelSerializer):
    """Simple serializer for creating BaseImage records after upload."""

    class Meta:
        model = BaseImage
        fields = ["id", "url", "s3_key", "width", "height", "filesize"]
        read_only_fields = ("id",)


class PostSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 게시글 요약."""

    image = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    matched_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "slug",
            "main_title",
            "is_editor_pick",
            "image",
            "tags",
            "matched_excerpt",
            "created_at",
        ]
        read_only_fields = fields

    def get_image(self, obj: Post):
        images = getattr(obj, "_prefetched_objects_cache", {}).get("images") if hasattr(obj, "_prefetched_objects_cache") else None
        if images is None:
            return None
        # search/home 요약은 썸네일을 우선 사용
        priority = {
            PostImagePurpose.THUMBNAIL: 0,
            PostImagePurpose.HEADER: 1,
            PostImagePurpose.HERO: 2,
            PostImagePurpose.BODY: 3,
        }
        sorted_imgs = sorted(images, key=lambda i: (priority.get(i.purpose, 99), i.order))
        if not sorted_imgs:
            return None
        img = sorted_imgs[0]
        return {"url": img.url, "purpose": img.purpose}

    def get_tags(self, obj: Post):
        tags = getattr(obj, "_prefetched_objects_cache", {}).get("tags") if hasattr(obj, "_prefetched_objects_cache") else None
        if tags is None:
            tags = list(obj.tags.all())
        return [{"id": str(tag.id), "name": tag.name} for tag in tags]

    def get_matched_excerpt(self, obj: Post):
        keyword = self.context.get("search_keyword")
        if not keyword:
            return None
        content = obj.content_md or _strip_html(obj.content_html)
        content = _normalize_whitespace(content)
        return _make_excerpt(content, keyword)

class RiderSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 라이더 요약."""

    location = serializers.CharField(source="region")
    bio = serializers.CharField(source="intro")
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "location", "bio", "profile_image"]
        read_only_fields = fields

    def get_profile_image(self, obj: User):
        image = getattr(obj, "profile_image", None)
        if not image:
            return None
        return {"url": image.url, "width": image.width, "height": image.height}


class BuildSearchSerializer(serializers.ModelSerializer):
    """검색 드롭다운용 빌드 요약(공개)."""

    main_image = serializers.SerializerMethodField()
    matched_components = serializers.SerializerMethodField()

    class Meta:
        model = BikeBuild
        fields = ["id", "title", "main_image", "matched_components"]
        read_only_fields = fields

    def get_main_image(self, obj: BikeBuild):
        image = getattr(obj, "main_image", None)
        if not image:
            return None
        return {"url": image.url, "width": image.width, "height": image.height}

    def get_matched_components(self, obj: BikeBuild):
        keyword = self.context.get("search_keyword")
        if not keyword:
            return []
        pattern = _build_word_pattern(keyword)
        if not pattern:
            return []
        components = getattr(obj, "components", None)
        if not isinstance(components, dict):
            return []
        matches: list[str] = []
        for items in components.values():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, str):
                    continue
                text = item.strip()
                if text and pattern.search(text):
                    matches.append(text)
        # preserve order, remove duplicates
        return list(dict.fromkeys(matches))


class GlobalSearchResponseSerializer(serializers.Serializer):
    """검색 응답 페이로드 구조."""

    query = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    sort = serializers.CharField(required=False)
    groups = serializers.DictField(required=False)
    items = serializers.ListField(required=False)
    page = serializers.IntegerField(required=False)
    page_size = serializers.IntegerField(required=False)
    has_more = serializers.BooleanField(required=False)


class MessageSerializer(serializers.Serializer):
    """통일된 메시지 래퍼."""

    message = serializers.CharField()


class GlobalSearchMessageSerializer(MessageSerializer):
    """통합 검색 래퍼."""

    data = GlobalSearchResponseSerializer()


class BaseImageUploadResponseSerializer(MessageSerializer):
    """이미지 업로드 응답 래퍼."""

    data = BaseImageUploadSerializer()


class HomePostSerializer(PostSearchSerializer):
    """홈 인기글 요약."""

    class Meta(PostSearchSerializer.Meta):
        fields = [
            "id",
            "slug",
            "main_title",
            "is_editor_pick",
            "image",
            "created_at",
        ]


class HomeBuildSerializer(BuildSearchSerializer):
    """홈 최신 빌드 요약."""

    rider = serializers.SerializerMethodField()

    class Meta(BuildSearchSerializer.Meta):
        fields = BuildSearchSerializer.Meta.fields + ["rider"]

    def get_rider(self, obj: BikeBuild):
        owner = getattr(obj.base_bike, "owner", None)
        if not owner:
            return None
        return {
            "id": str(owner.id),
            "name": owner.username,
        }


class HomeDataSerializer(serializers.Serializer):
    """홈 응답 데이터."""

    posts = HomePostSerializer(many=True)


class HomeResponseSerializer(MessageSerializer):
    """홈 응답 래퍼."""

    data = HomeDataSerializer()
