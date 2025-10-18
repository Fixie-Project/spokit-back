"""게시글 관련 직렬화기 모음."""
from __future__ import annotations

from rest_framework import serializers

from app.bike.serializers import BikeSerializer, BikeBuildSerializer
from app.submission.models import Submission

from .models import Comment, Post, PostImage, PostStatus, Tag


class TagSerializer(serializers.ModelSerializer):
    """태그 정보를 직렬화."""

    class Meta:
        model = Tag
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    """게시글 댓글 데이터를 직렬화."""

    user = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "created_at"]
        read_only_fields = fields


class PostImageSerializer(serializers.ModelSerializer):
    """게시글과 연결된 이미지 정보를 직렬화."""

    class Meta:
        model = PostImage
        fields = [
            "id",
            "url",
            "purpose",
            "order",
            "caption",
            "created_at",
        ]
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    """게시글을 조회할 때 필요한 상세 정보를 제공."""

    tags = TagSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    submission = serializers.SerializerMethodField()
    bike = BikeSerializer(read_only=True)
    build = BikeBuildSerializer(read_only=True)
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "submission",
            "bike",
            "build",
            "build_snapshot",
            "rider",
            "main_title",
            "sub_title",
            "content_md",
            "content_html",
            "content_json",
            "frame_brand",
            "frame_type",
            "slug",
            "status",
            "published_at",
            "created_at",
            "updated_at",
            "tags",
            "images",
            "like_count",
        ]
        read_only_fields = (
            "id",
            "author",
            "submission",
            "bike",
            "build",
            "build_snapshot",
            "rider",
            "published_at",
            "created_at",
            "updated_at",
            "tags",
            "images",
            "like_count",
        )

    def get_submission(self, obj: Post):
        submission: Submission | None = getattr(obj, "submission", None)
        if not submission:
            return None
        return {
            "id": str(submission.id),
            "status": submission.status,
        }


class PostWriteSerializer(serializers.ModelSerializer):
    """게시글 생성·수정 시 사용하는 직렬화기."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Post
        fields = [
            "author",
            "submission",
            "bike",
            "build",
            "build_snapshot",
            "rider",
            "main_title",
            "sub_title",
            "content_md",
            "content_html",
            "content_json",
            "frame_brand",
            "frame_type",
            "slug",
            "status",
            "tags",
        ]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        post = super().create(validated_data)
        if tags:
            post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        post = super().update(instance, validated_data)
        if tags is not None:
            post.tags.set(tags)
        return post
