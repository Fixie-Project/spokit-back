"""Studio-only serializers for staff-facing views."""
from __future__ import annotations

from rest_framework import serializers

from app.post.models import Post
from app.post.serializers import PostSerializer
from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.user.models import User


class RiderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "nickname", "region", "intro", "sns_link"]
        read_only_fields = fields


class StudioSubmissionSerializer(SubmissionSerializer):
    """확장된 신청서 직렬화기(운영진 뷰용)."""

    rider = RiderSummarySerializer(source="user", read_only=True)

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + ["rider"]
        read_only_fields = SubmissionSerializer.Meta.read_only_fields


class SubmissionStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SubmissionStatus.choices)
    reason_code = serializers.CharField(required=False, allow_blank=True)
    reason_detail = serializers.CharField(required=False, allow_blank=True)


class SubmissionSummarySerializer(serializers.ModelSerializer):
    rider = RiderSummarySerializer(source="user", read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "title", "status", "created_at", "updated_at", "rider"]
        read_only_fields = fields


class SubmissionPreviewSerializer(serializers.ModelSerializer):
    """포스트 작성 전 미리보기용 최소 필드."""

    rider = RiderSummarySerializer(source="user", read_only=True)
    bike_frame = serializers.CharField(source="bike.frame_name", read_only=True)
    build_title = serializers.CharField(source="build.title", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "status",
            "created_at",
            "updated_at",
            "rider",
            "bike_frame",
            "build_title",
        ]
        read_only_fields = fields


class PostSummarySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    rider = RiderSummarySerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "main_title",
            "sub_title",
            "slug",
            "status",
            "published_at",
            "updated_at",
            "author_name",
            "rider",
        ]
        read_only_fields = fields

    def get_author_name(self, obj: Post) -> str | None:
        staff = getattr(obj, "author", None)
        user = getattr(staff, "user", None) if staff else None
        if not user:
            return None
        return user.nickname or user.username


class PostStudioSerializer(PostSerializer):
    """운영진 전용 게시글 직렬화기."""

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["view_count"]
        read_only_fields = PostSerializer.Meta.read_only_fields + ("view_count",)


class MessageSerializer(serializers.Serializer):
    """응답 메시지 래퍼."""

    message = serializers.CharField()


class StudioSubmissionListResponseSerializer(MessageSerializer):
    """운영진 신청서 목록 응답."""

    data = SubmissionPreviewSerializer(many=True)


class StudioSubmissionDetailDataSerializer(serializers.Serializer):
    """운영진 신청서 상세 래퍼 데이터."""

    submission = StudioSubmissionSerializer()


class StudioSubmissionDetailResponseSerializer(MessageSerializer):
    """운영진 신청서 상세 응답."""

    data = StudioSubmissionDetailDataSerializer()


class StudioSubmissionUpdateResponseSerializer(MessageSerializer):
    """운영진 신청서 수정/상태 변경 응답."""

    data = StudioSubmissionSerializer()


class StudioPostListResponseSerializer(MessageSerializer):
    """운영진 게시글 목록 응답."""

    data = PostStudioSerializer(many=True)


class StudioPostDetailDataSerializer(serializers.Serializer):
    """운영진 게시글 상세 래퍼 데이터."""

    post = PostStudioSerializer()


class StudioPostDetailResponseSerializer(MessageSerializer):
    """운영진 게시글 상세 응답."""

    data = StudioPostDetailDataSerializer()


class StudioPostResponseSerializer(MessageSerializer):
    """운영진 게시글 생성/수정 응답."""

    data = PostStudioSerializer()


class StudioDashboardDataSerializer(serializers.Serializer):
    """대시보드 응답 데이터."""

    total_pending = serializers.IntegerField()
    total_posting = serializers.IntegerField()
    pending = SubmissionSerializer(many=True)
    posting = SubmissionSerializer(many=True)
    pending_top = SubmissionSummarySerializer(many=True)
    posting_top = SubmissionSummarySerializer(many=True)
    status_counts = serializers.DictField(child=serializers.IntegerField())
    post_status_counts = serializers.DictField(child=serializers.IntegerField())
    total_published_posts = serializers.IntegerField()
    total_working_posts = serializers.IntegerField()
    total_draft_posts = serializers.IntegerField()
    total_rejected_submissions = serializers.IntegerField()
    total_pending_submissions = serializers.IntegerField()
    working_posts = PostSummarySerializer(many=True)
    stats_last_updated = serializers.DateTimeField()


class StudioDashboardResponseSerializer(MessageSerializer):
    """대시보드 응답 래퍼."""

    data = StudioDashboardDataSerializer()
