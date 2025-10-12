"""스태프 전용 신청 관리 API 모음입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.studio.models import SubmissionReviewNote


class StaffRequired(permissions.BasePermission):
    """스태프 여부를 검사하는 커스텀 권한 클래스."""

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.is_staff


class ReviewNoteSerializer(serializers.ModelSerializer):
    """검토 메모 직렬화기 (읽기 전용 필드 포함)."""

    class Meta:
        model = SubmissionReviewNote
        fields = ["id", "author", "post", "post_status", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "post", "created_at", "updated_at"]


class StudioDashboardAPIView(views.APIView):
    """대시보드용 신청 현황 요약을 반환합니다."""

    permission_classes = [StaffRequired]

    def get(self, request) -> Response:
        pending = Submission.objects.filter(
            status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]
        ).select_related("bike", "bike__spec")
        in_progress = Submission.objects.filter(status=SubmissionStatus.IN_PROGRESS)
        payload = {
            "total_pending": pending.count(),
            "total_in_progress": in_progress.count(),
            "pending": SubmissionSerializer(pending, many=True, context={"request": request}).data,
            "in_progress": SubmissionSerializer(in_progress, many=True, context={"request": request}).data,
        }
        return Response(payload)


class StudioSubmissionDetailAPIView(views.APIView):
    """특정 신청 세부 정보와 검토 메모를 관리합니다."""

    permission_classes = [StaffRequired]

    def get_object(self, pk: int) -> Submission:
        return get_object_or_404(
            Submission.objects.select_related("bike", "bike__spec").prefetch_related("images", "review_notes"),
            pk=pk,
        )

    def get(self, request, pk: int) -> Response:
        submission = self.get_object(pk)
        serializer = SubmissionSerializer(submission, context={"request": request})
        notes = ReviewNoteSerializer(submission.review_notes.all(), many=True).data
        return Response({"submission": serializer.data, "review_notes": notes})

    def patch(self, request, pk: int) -> Response:
        submission = self.get_object(pk)
        serializer = SubmissionSerializer(
            submission,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StudioReviewNoteAPIView(views.APIView):
    """신청에 대한 검토 메모를 작성합니다."""

    permission_classes = [StaffRequired]

    def post(self, request, pk: int) -> Response:
        submission = get_object_or_404(Submission, pk=pk)
        serializer = ReviewNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = SubmissionReviewNote.objects.create(
            submission=submission,
            author=request.user,
            post_status=serializer.validated_data.get("post_status", ""),
            note=serializer.validated_data.get("note", ""),
        )
        return Response(ReviewNoteSerializer(note).data, status=status.HTTP_201_CREATED)
