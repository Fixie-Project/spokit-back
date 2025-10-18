"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from app.submission.models import Submission, SubmissionStatus

from .models import Post, PostStatus
from .serializers import PostSerializer, PostWriteSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Posts"],
        summary="게시글 목록 조회",
        description="발행된 게시글 목록을 반환합니다. 관리자는 모든 상태의 게시글을 확인할 수 있습니다.",
    ),
    retrieve=extend_schema(
        tags=["Posts"],
        summary="특정 게시글 조회",
        description="게시글 상세 정보를 반환합니다. 비회원은 발행된 게시글만 조회할 수 있습니다.",
    ),
    create=extend_schema(
        tags=["Posts"],
        summary="게시글 생성 (관리자 전용)",
    ),
    partial_update=extend_schema(
        tags=["Posts"],
        summary="게시글 부분 수정 (관리자 전용)",
    ),
    destroy=extend_schema(
        tags=["Posts"],
        summary="게시글 삭제 (관리자 전용)",
    ),
)
class PostViewSet(viewsets.ModelViewSet):
    """게시글 CRUD API."""

    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = (
        Post.objects.select_related("author", "submission", "bike", "build", "rider")
        .prefetch_related("tags", "likes")
        .all()
    )

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PostWriteSerializer
        return PostSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(status=PostStatus.PUBLISHED)
        return qs

    def perform_create(self, serializer):
        staff = getattr(self.request.user, "staff_profile", None)
        post = serializer.save(author=staff)
        submission = post.submission
        if submission and submission.status not in {SubmissionStatus.PUBLISHED, SubmissionStatus.POSTING}:
            submission.status = SubmissionStatus.POSTING
            submission.save(update_fields=["status", "updated_at"])

    def perform_update(self, serializer):
        post = serializer.save()
        submission = post.submission
        if submission and submission.status == SubmissionStatus.POSTING and post.status == PostStatus.PUBLISHED:
            submission.status = SubmissionStatus.PUBLISHED
            submission.save(update_fields=["status", "updated_at"])

    def perform_destroy(self, instance):
        if instance.submission_id:
            Submission.objects.filter(pk=instance.submission_id).update(status=SubmissionStatus.APPROVED)
        super().perform_destroy(instance)
