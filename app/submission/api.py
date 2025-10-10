"""소개 신청 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Submission
from .questions import DEFAULT_QUESTION_VERSION, load_question_set
from .serializers import SubmissionSerializer


@extend_schema_view(
    list=extend_schema(tags=["Submissions"], summary="소개 신청 목록 조회"),
    retrieve=extend_schema(tags=["Submissions"], summary="소개 신청 상세 조회"),
    create=extend_schema(tags=["Submissions"], summary="소개 신청 생성"),
    update=extend_schema(tags=["Submissions"], summary="소개 신청 전체 수정"),
    partial_update=extend_schema(tags=["Submissions"], summary="소개 신청 부분 수정"),
    destroy=extend_schema(tags=["Submissions"], summary="소개 신청 삭제"),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    """소개 신청서 CRUD를 제공하는 API."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Submission.objects.filter(user=self.request.user)
            .select_related("bike", "bike__spec", "result_post")
            .prefetch_related("images")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class QuestionSetView(APIView):
    """버전별 질문 세트를 내려줍니다."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(tags=["Submissions"], summary="질문 세트 조회")
    def get(self, request, *args, **kwargs):
        version = request.query_params.get("version") or DEFAULT_QUESTION_VERSION
        question_set = load_question_set(version)
        payload = {
            "version": question_set.version,
            "group_labels": question_set.group_labels,
            "groups": question_set.groups,
            "questions": question_set.questions,
            "metadata": question_set.metadata,
        }
        return Response(payload)
