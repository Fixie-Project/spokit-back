"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from app.submission.models import Submission, SubmissionStatus

from .models import Post
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
        Post.objects.select_related("author")
        .prefetch_related("tags", "likes", "source_submissions")
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
            qs = qs.filter(status="published")
        return qs

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        submission_id = self.request.data.get("submission")
        if submission_id:
            submission = Submission.objects.filter(pk=submission_id).first()
            if submission:
                submission.result_post = post
                if submission.status not in {SubmissionStatus.PUBLISHED, SubmissionStatus.IN_PROGRESS}:
                    submission.status = SubmissionStatus.IN_PROGRESS
                submission.save(update_fields=["result_post", "status"])

    def perform_update(self, serializer):
        post = serializer.save()
        submission_id = self.request.data.get("submission")
        if submission_id:
            submission = Submission.objects.filter(pk=submission_id).first()
            if submission and submission.result_post_id != post.id:
                submission.result_post = post
                submission.save(update_fields=["result_post"])

    def perform_destroy(self, instance):
        Submission.objects.filter(result_post=instance).update(result_post=None)
        super().perform_destroy(instance)
