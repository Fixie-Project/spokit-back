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
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
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
            "story_snapshot",
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
            "is_editor_pick",
            "tags",
            "images",
            "like_count",
            "comment_count",
            "is_liked",
        ]
        read_only_fields = (
            "id",
            "author",
            "submission",
            "bike",
            "build",
            "build_snapshot",
            "story_snapshot",
            "rider",
            "published_at",
            "created_at",
            "updated_at",
            "view_count",
            "is_editor_pick",
            "tags",
            "images",
            "like_count",
            "comment_count",
            "is_liked",
        )

    def get_submission(self, obj: Post):
        submission: Submission | None = getattr(obj, "submission", None)
        if not submission:
            return None
        return {
            "id": str(submission.id),
            "status": submission.status,
        }

    def get_comment_count(self, obj: Post) -> int:
        count = getattr(obj, "comment_count", None)
        if count is not None:
            return count
        return obj.comments.count()

    def get_is_liked(self, obj: Post) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        prefetched_likes = obj._prefetched_objects_cache.get("likes") if hasattr(obj, "_prefetched_objects_cache") else None
        if prefetched_likes is not None:
            return any(like.user_id == user.id for like in prefetched_likes)
        return obj.likes.filter(user=user).exists()


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
            "is_editor_pick",
            "tags",
        ]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        post = super().create(validated_data)
        if tags:
            post.tags.set(tags)
        if post.sync_snapshots_from_submission(force=True):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        post = super().update(instance, validated_data)
        if tags is not None:
            post.tags.set(tags)
        if post.sync_snapshots_from_submission(force=False):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        return post


class PostDetailSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["view_count"]
        read_only_fields = PostSerializer.Meta.read_only_fields + ("view_count",)
