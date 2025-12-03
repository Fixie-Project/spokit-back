"""스태프 전용 신청 관리 API 모음입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import views, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.user.models import Staff
from app.user.permissions import IsAdminRole, IsStaffUser
from app.user.serializers import StaffSerializer
from .serializers import StudioSubmissionSerializer, SubmissionStatusUpdateSerializer


class StudioDashboardAPIView(views.APIView):
    """대시보드용 신청 현황 요약을 반환합니다."""

    permission_classes = [IsStaffUser]

    def get(self, request) -> Response:
        pending = Submission.objects.filter(
            status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]
        ).select_related("bike", "build")
        posting = Submission.objects.filter(status=SubmissionStatus.POSTING)
        payload = {
            "total_pending": pending.count(),
            "total_posting": posting.count(),
            "pending": SubmissionSerializer(pending, many=True, context={"request": request}).data,
            "posting": SubmissionSerializer(posting, many=True, context={"request": request}).data,
        }
        return Response(payload)


class StudioSubmissionListAPIView(views.APIView):
    """운영진 전용 신청서 전체 목록/필터."""

    permission_classes = [IsStaffUser]

    @extend_schema(tags=["Studio"], summary="신청서 목록(운영진)")
    def get(self, request) -> Response:
        status_filter = request.query_params.get("status")
        qs = Submission.objects.select_related("user", "bike", "build").prefetch_related("images")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-created_at")
        serializer = StudioSubmissionSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class StudioSubmissionDetailAPIView(views.APIView):
    """특정 신청 세부 정보를 조회·수정합니다."""

    permission_classes = [IsStaffUser]

    def get_object(self, pk: str) -> Submission:
        return get_object_or_404(
            Submission.objects.select_related("bike", "build").prefetch_related("images"),
            pk=pk,
        )

    def get(self, request, pk: str) -> Response:
        submission = self.get_object(pk)
        serializer = StudioSubmissionSerializer(submission, context={"request": request})
        return Response({"submission": serializer.data})

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
        return Response(serializer.data)


class StudioSubmissionStatusAPIView(views.APIView):
    """신청서 상태만 변경 (운영진)."""

    permission_classes = [IsStaffUser]

    def get_object(self, pk: str) -> Submission:
        return get_object_or_404(Submission, pk=pk)

    @extend_schema(tags=["Studio"], summary="신청서 상태 변경", request=SubmissionStatusUpdateSerializer)
    def patch(self, request, pk: str) -> Response:
        submission = self.get_object(pk)
        serializer = SubmissionStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_status = serializer.validated_data["status"]
        reason_code = serializer.validated_data.get("reason_code", "")
        reason_detail = serializer.validated_data.get("reason_detail", "")

        # 간단한 전이만 허용: in_review/approved/rejected/posting/published
        allowed = {
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.IN_REVIEW,
            SubmissionStatus.APPROVED,
            SubmissionStatus.POSTING,
            SubmissionStatus.PUBLISHED,
            SubmissionStatus.REJECTED,
        }
        if target_status not in allowed:
            return Response({"status": ["이 상태로는 변경할 수 없습니다."]}, status=status.HTTP_400_BAD_REQUEST)

        submission.status = target_status
        submission.reason_code = reason_code
        submission.reason_detail = reason_detail
        submission.save(update_fields=["status", "reason_code", "reason_detail", "updated_at"])

        return Response(StudioSubmissionSerializer(submission, context={"request": request}).data)


class StaffDetailAPIView(views.APIView):
    """운영진 계정 정보를 조회/수정합니다."""

    permission_classes = [IsAdminRole]

    def get_object(self, pk: str) -> Staff:
        return get_object_or_404(Staff.objects.select_related("user"), pk=pk)

    def get(self, request, pk: str) -> Response:
        staff = self.get_object(pk)
        serializer = StaffSerializer(staff, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        request=StaffSerializer,
        responses=StaffSerializer,
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
        return Response(serializer.data)
