"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from django.db.models import Count, F, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from app.submission.models import Submission, SubmissionStatus
from app.submission.services import change_submission_status
from app.user.permissions import IsEditorOrAdmin

from .models import Post, PostStatus
from .serializers import PostDetailSerializer, PostSerializer, PostWriteSerializer

PUBLIC_TAG = "Public"


@extend_schema_view(
    list=extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="게시글 목록 조회",
        description="발행된 게시글 목록을 반환합니다. 관리자는 모든 상태의 게시글을 확인할 수 있습니다.",
    ),
    retrieve=extend_schema(
        tags=["Posts", PUBLIC_TAG],
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
        .prefetch_related("tags", "likes", "images")
        .annotate(comment_count=Count("comments", distinct=True))
    )

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [permissions.IsAuthenticated(), IsEditorOrAdmin()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PostWriteSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(status=PostStatus.PUBLISHED)
        query = self.request.query_params.get("q")
        if query:
            qs = qs.filter(
                Q(main_title__icontains=query)
                | Q(sub_title__icontains=query)
                | Q(content_md__icontains=query)
                | Q(frame_brand__icontains=query)
            )
        return qs

    def perform_create(self, serializer):
        staff = getattr(self.request.user, "staff_profile", None)
        post = serializer.save(author=staff)
        if post.sync_snapshots_from_submission(force=True):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        submission = post.submission
        if submission and submission.status not in {SubmissionStatus.PUBLISHED, SubmissionStatus.POSTING}:
            change_submission_status(
                submission,
                to_status=SubmissionStatus.POSTING,
                actor=self.request.user,
            )

    def perform_update(self, serializer):
        post = serializer.save()
         # if snapshots empty, populate once
        if post.sync_snapshots_from_submission(force=False):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        submission = post.submission
        if submission and submission.status == SubmissionStatus.POSTING and post.status == PostStatus.PUBLISHED:
            change_submission_status(
                submission,
                to_status=SubmissionStatus.PUBLISHED,
                actor=self.request.user,
            )

    def perform_destroy(self, instance):
        if instance.submission_id:
            submission = Submission.objects.filter(pk=instance.submission_id).first()
            if submission and submission.status != SubmissionStatus.APPROVED:
                change_submission_status(
                    submission,
                    to_status=SubmissionStatus.APPROVED,
                    actor=self.request.user,
                )
        super().perform_destroy(instance)

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status == PostStatus.PUBLISHED:
            Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
            post.view_count += 1
        serializer = self.get_serializer(post)
        return Response(serializer.data)
