"""스태프 전용 신청 관리 API 모음입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import views
from rest_framework.response import Response

from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.user.models import Staff
from app.user.permissions import IsAdminRole, IsStaffUser
from app.user.serializers import StaffSerializer


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
        serializer = SubmissionSerializer(submission, context={"request": request})
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


class StaffDetailAPIView(views.APIView):
    """운영진 계정 정보를 조회/수정합니다."""

    permission_classes = [IsAdminRole]

    def get_object(self, pk: str) -> Staff:
        return get_object_or_404(Staff.objects.select_related("user"), pk=pk)

    def get(self, request, pk: str) -> Response:
        staff = self.get_object(pk)
        serializer = StaffSerializer(staff, context={"request": request})
        return Response(serializer.data)

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
