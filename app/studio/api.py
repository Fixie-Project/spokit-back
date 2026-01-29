"""스태프 전용 신청 관리 API 모음입니다."""
from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from app.core.responses import success_response
from app.post.models import Post, PostStatus
from app.post.serializers import PostWriteSerializer
from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.submission.services import change_submission_status
from app.user.models import Staff
from app.user.permissions import IsAdminRole, IsEditorOrAdmin, IsStaffUser
from app.user.serializers import StaffResponseSerializer, StaffSerializer
from .serializers import (
    MessageSerializer,
    PostSummarySerializer,
    PostStudioSerializer,
    StudioSubmissionSerializer,
    SubmissionPreviewSerializer,
    SubmissionStatusUpdateSerializer,
    SubmissionSummarySerializer,
    StudioDashboardResponseSerializer,
    StudioPostDetailResponseSerializer,
    StudioPostListResponseSerializer,
    StudioPostResponseSerializer,
    StudioSubmissionDetailResponseSerializer,
    StudioSubmissionListResponseSerializer,
    StudioSubmissionUpdateResponseSerializer,
)


def _publish_submission_if_needed(post: Post, actor) -> None:
    submission = getattr(post, "submission", None)
    if not submission or post.status != PostStatus.PUBLISHED:
        return
    if submission.status == SubmissionStatus.PUBLISHED:
        return
    try:
        change_submission_status(
            submission,
            to_status=SubmissionStatus.PUBLISHED,
            actor=actor,
        )
    except DjangoValidationError as exc:
        payload = exc.message_dict if hasattr(exc, "message_dict") else {"submission": exc.messages}
        raise ValidationError(payload) from exc


class StudioDashboardAPIView(views.APIView):
    """대시보드용 신청 현황 요약을 반환합니다."""

    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["Studio"],
        summary="대시보드 요약",
        responses=StudioDashboardResponseSerializer,
    )
    def get(self, request) -> Response:
        raw_limit = request.query_params.get("limit")
        try:
            limit = int(raw_limit) if raw_limit else 5
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 50))

        pending = (
            Submission.objects.filter(status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW])
            .select_related("bike", "build")
            .order_by("-created_at")
        )
        posting = (
            Submission.objects.filter(status=SubmissionStatus.APPROVED)
            .select_related("bike", "build")
            .order_by("-created_at")
        )

        status_counts = {
            row["status"]: row["total"]
            for row in Submission.objects.values("status").annotate(total=Count("id"))
        }

        post_status_counts = {
            row["status"]: row["total"]
            for row in Post.objects.values("status").annotate(total=Count("id"))
        }

        total_pending_submissions = status_counts.get(SubmissionStatus.SUBMITTED, 0) + status_counts.get(
            SubmissionStatus.IN_REVIEW, 0
        )
        total_rejected_submissions = status_counts.get(SubmissionStatus.REJECTED, 0)
        total_draft_posts = post_status_counts.get(PostStatus.DRAFT, 0)
        total_published_posts = post_status_counts.get(PostStatus.PUBLISHED, 0)
        total_working_posts = post_status_counts.get(PostStatus.DRAFT, 0) + post_status_counts.get(PostStatus.REVIEW, 0)

        working_posts = (
            Post.objects.filter(status__in=[PostStatus.DRAFT, PostStatus.REVIEW])
            .select_related("author__user", "rider")
            .order_by("-updated_at")[:limit]
        )

        pending_top = pending[:limit]
        posting_top = posting[:limit]
        payload = {
            "total_pending": pending.count(),
            "total_posting": posting.count(),
            "pending": SubmissionSerializer(pending, many=True, context={"request": request}).data,
            "posting": SubmissionSerializer(posting, many=True, context={"request": request}).data,
            "pending_top": SubmissionSummarySerializer(
                pending_top, many=True, context={"request": request}
            ).data,
            "posting_top": SubmissionSummarySerializer(
                posting_top, many=True, context={"request": request}
            ).data,
            "status_counts": status_counts,
            "post_status_counts": post_status_counts,
            "total_published_posts": total_published_posts,
            "total_working_posts": total_working_posts,
            "total_draft_posts": total_draft_posts,
            "total_rejected_submissions": total_rejected_submissions,
            "total_pending_submissions": total_pending_submissions,
            "working_posts": PostSummarySerializer(
                working_posts, many=True, context={"request": request}
            ).data,
            "stats_last_updated": timezone.now(),
        }
        return success_response("대시보드를 조회했습니다.", payload)


class StudioSubmissionListAPIView(views.APIView):
    """운영진 전용 신청서 전체 목록/필터."""

    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["Studio"],
        summary="신청서 목록(운영진)",
        responses=StudioSubmissionListResponseSerializer,
    )
    def get(self, request) -> Response:
        status_filter = request.query_params.get("status")
        qs = Submission.objects.select_related("user", "bike", "build").prefetch_related("images")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-created_at")
        serializer = SubmissionPreviewSerializer(qs, many=True, context={"request": request})
        return success_response("신청서 목록을 조회했습니다.", serializer.data)


class StudioSubmissionDetailAPIView(views.APIView):
    """특정 신청 세부 정보를 조회·수정합니다."""

    permission_classes = [IsStaffUser]

    def get_object(self, pk: str) -> Submission:
        return get_object_or_404(
            Submission.objects.select_related("bike", "build").prefetch_related("images"),
            pk=pk,
        )

    @extend_schema(
        tags=["Studio"],
        summary="신청서 상세(운영진)",
        responses=StudioSubmissionDetailResponseSerializer,
    )
    def get(self, request, pk: str) -> Response:
        submission = self.get_object(pk)
        if submission.status == SubmissionStatus.SUBMITTED:
            submission = change_submission_status(
                submission,
                to_status=SubmissionStatus.IN_REVIEW,
                actor=request.user,
            )
        serializer = StudioSubmissionSerializer(submission, context={"request": request})
        return success_response("신청서를 조회했습니다.", {"submission": serializer.data})

    @extend_schema(
        tags=["Studio"],
        summary="신청서 수정(운영진)",
        responses=StudioSubmissionUpdateResponseSerializer,
    )
    def patch(self, request, pk: str) -> Response:
        submission = self.get_object(pk)
        serializer = SubmissionSerializer(
            submission,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("신청서를 수정했습니다.", serializer.data)


class StudioSubmissionStatusAPIView(views.APIView):
    """신청서 상태만 변경 (운영진)."""

    permission_classes = [IsStaffUser]

    def get_object(self, pk: str) -> Submission:
        return get_object_or_404(Submission, pk=pk)

    @extend_schema(
        tags=["Studio"],
        summary="신청서 상태 변경",
        request=SubmissionStatusUpdateSerializer,
        responses=StudioSubmissionUpdateResponseSerializer,
    )
    def patch(self, request, pk: str) -> Response:
        submission = self.get_object(pk)
        serializer = SubmissionStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_status = serializer.validated_data["status"]
        reason_code = serializer.validated_data.get("reason_code", "")
        reason_detail = serializer.validated_data.get("reason_detail", "")

        # 간단한 전이만 허용: submitted/in_review/approved/rejected/published
        allowed = {
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.IN_REVIEW,
            SubmissionStatus.APPROVED,
            SubmissionStatus.REJECTED,
            SubmissionStatus.PUBLISHED,
        }
        if target_status not in allowed:
            return Response({"status": ["이 상태로는 변경할 수 없습니다."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            submission = change_submission_status(
                submission,
                to_status=target_status,
                actor=request.user,
                comment=reason_detail,
                reason_code=reason_code or None,
                reason_detail=reason_detail,
            )
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"status": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        return success_response(
            "신청서 상태를 변경했습니다.",
            StudioSubmissionSerializer(submission, context={"request": request}).data,
        )


class StaffDetailAPIView(views.APIView):
    """운영진 계정 정보를 조회/수정합니다."""

    permission_classes = [IsAdminRole]

    def get_object(self, pk: str) -> Staff:
        return get_object_or_404(Staff.objects.select_related("user"), pk=pk)

    @extend_schema(
        responses=StaffResponseSerializer,
        tags=["Studio"],
        summary="운영진 정보 조회",
    )
    def get(self, request, pk: str) -> Response:
        staff = self.get_object(pk)
        serializer = StaffSerializer(staff, context={"request": request})
        return success_response("운영진 정보를 조회했습니다.", serializer.data)

    @extend_schema(
        request=StaffSerializer,
        responses=StaffResponseSerializer,
        tags=["Studio"],
        summary="운영진 정보 수정",
    )
    def patch(self, request, pk: str) -> Response:
        staff = self.get_object(pk)
        serializer = StaffSerializer(
            staff,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("운영진 정보를 수정했습니다.", serializer.data)


class StudioPostListAPIView(views.APIView):
    """운영진 전용 게시글 목록/검색/필터/생성."""

    permission_classes = [IsEditorOrAdmin]

    @extend_schema(tags=["Studio"], summary="게시글 목록(운영진)", responses=StudioPostListResponseSerializer)
    def get(self, request) -> Response:
        qs = (
            Post.objects.select_related("author__user", "submission", "bike", "build", "rider")
            .prefetch_related("tags", "images")
            .annotate(comment_count=Count("comments", distinct=True))
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        query = request.query_params.get("q")
        if query:
            qs = qs.filter(
                Q(main_title__icontains=query)
                | Q(sub_title__icontains=query)
                | Q(frame_brand__icontains=query)
                | Q(content_md__icontains=query)
            )

        ordering = request.query_params.get("ordering", "-updated_at")
        allowed_ordering = {
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "published_at",
            "-published_at",
        }
        if ordering not in allowed_ordering:
            ordering = "-updated_at"
        qs = qs.order_by(ordering)

        serializer = PostStudioSerializer(qs, many=True, context={"request": request})
        return success_response("게시글 목록을 조회했습니다.", serializer.data)

    @extend_schema(
        tags=["Studio"],
        summary="게시글 생성(운영진)",
        request=PostWriteSerializer,
        responses=StudioPostResponseSerializer,
    )
    def post(self, request) -> Response:
        serializer = PostWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        submission = serializer.validated_data.get("submission")
        if submission and submission.status != SubmissionStatus.APPROVED:
            raise ValidationError({"submission": "승인된 신청서만 게시글과 연결할 수 있습니다."})

        staff = getattr(request.user, "staff_profile", None)
        post = serializer.save(author=staff)

        if post.sync_snapshots_from_submission(force=True):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])

        if post.status == PostStatus.PUBLISHED and post.bike_id:
            post.bike.is_posted = True
            post.bike.save(update_fields=["is_posted", "updated_at"])

        _publish_submission_if_needed(post, request.user)
        return success_response(
            "게시글을 생성했습니다.",
            PostStudioSerializer(post, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class StudioPostDetailAPIView(views.APIView):
    """운영진 전용 게시글 단건 조회/수정."""

    permission_classes = [IsEditorOrAdmin]

    def get_object(self, slug: str) -> Post:
        return get_object_or_404(
            Post.objects.select_related("author__user", "submission", "bike", "build", "rider")
            .prefetch_related("tags", "images")
            .annotate(comment_count=Count("comments", distinct=True)),
            slug=slug,
        )

    @extend_schema(
        tags=["Studio"],
        summary="게시글 상세(운영진)",
        responses=StudioPostDetailResponseSerializer,
    )
    def get(self, request, slug: str) -> Response:
        post = self.get_object(slug)
        serializer = PostStudioSerializer(post, context={"request": request})
        return success_response("게시글을 조회했습니다.", {"post": serializer.data})

    @extend_schema(
        tags=["Studio"],
        summary="게시글 수정(운영진)",
        request=PostWriteSerializer,
        responses=StudioPostResponseSerializer,
    )
    def patch(self, request, slug: str) -> Response:
        post = self.get_object(slug)
        serializer = PostWriteSerializer(
            post,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        post = serializer.save()

        if post.sync_snapshots_from_submission(force=False):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])

        submission = post.submission
        if submission and submission.status not in {SubmissionStatus.APPROVED, SubmissionStatus.PUBLISHED}:
            return Response(
                {"submission": ["승인된 신청서만 게시글과 연결할 수 있습니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if post.status == PostStatus.PUBLISHED and post.bike_id:
            post.bike.is_posted = True
            post.bike.save(update_fields=["is_posted", "updated_at"])

        _publish_submission_if_needed(post, request.user)
        return success_response(
            "게시글을 수정했습니다.",
            PostStudioSerializer(post, context={"request": request}).data,
        )

    @extend_schema(tags=["Studio"], summary="게시글 삭제(운영진)", responses=MessageSerializer)
    def delete(self, request, slug: str) -> Response:
        post = self.get_object(slug)
        post.delete()
        return success_response("게시글을 삭제했습니다.")
