"""게시글과 관련된 직렬화 도구입니다."""
from __future__ import annotations

from rest_framework import serializers

from app.bike.serializers import BikeSerializer
from app.submission.models import Submission

from .models import Comment, Post, Tag


class TagSerializer(serializers.ModelSerializer):
    """태그 정보를 직렬화합니다."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "description"]


class CommentSerializer(serializers.ModelSerializer):
    """댓글 정보를 직렬화합니다."""

    user = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "is_blocked", "created_at"]
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    """게시글과 관련된 주요 정보를 직렬화합니다."""

    tags = TagSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "body",
            "cover_image",
            "spec",
            "status",
            "featured",
            "published_at",
            "updated_at",
            "tags",
            "like_count",
            "submission",
        ]
        read_only_fields = ("id", "published_at", "updated_at", "tags", "like_count", "submission")

    def get_submission(self, obj: Post):
        submission = Submission.objects.filter(result_post=obj).select_related("bike", "bike__spec").first()
        if not submission:
            return None
        return {
            "id": submission.id,
            "status": submission.status,
            "bike": BikeSerializer(submission.bike).data if submission.bike else None,
        }
