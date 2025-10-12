"""사용자 마이페이지 관련 API 뷰입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, views
from rest_framework.response import Response

from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer


class UserSubmissionListAPIView(views.APIView):
    """로그인 사용자의 신청 목록을 반환합니다."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        submissions = (
            Submission.objects.filter(user=request.user)
            .select_related("bike", "bike__spec")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        serializer = SubmissionSerializer(submissions, many=True, context={"request": request})
        return Response({"count": submissions.count(), "results": serializer.data})


class UserSubmissionDetailAPIView(views.APIView):
    """특정 신청을 조회하거나 수정합니다."""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk: int) -> Submission:
        return get_object_or_404(Submission, pk=pk, user=request.user)

    def get(self, request, pk: int) -> Response:
        submission = self.get_object(request, pk)
        serializer = SubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk: int) -> Response:
        submission = self.get_object(request, pk)
        serializer = SubmissionSerializer(
            submission,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserProfileSummaryAPIView(views.APIView):
    """신청 상태별 통계 요약을 제공합니다."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        submissions = Submission.objects.filter(user=request.user)
        stats = {
            "total": submissions.count(),
            "by_status": {
                status: submissions.filter(status=status).count()
                for status in SubmissionStatus.values
            },
        }
        return Response(stats)
