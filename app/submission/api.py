"""소개 신청 관련 API 뷰셋입니다."""
from __future__ import annotations

from rest_framework import permissions, viewsets

from .models import Submission
from .serializers import SubmissionSerializer


class SubmissionViewSet(viewsets.ModelViewSet):
    """소개 신청서 CRUD를 제공하는 API."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).select_related(
            "bike", "bike__spec", "result_post"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
