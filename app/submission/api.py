"""소개 신청 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app.user.permissions import IsEditorOrAdmin, IsStaffUser

from .models import Submission, SubmissionStatus
from .questions import DEFAULT_QUESTION_VERSION, load_question_set
from .serializers import (
    SubmissionCommentSerializer,
    SubmissionRejectSerializer,
    SubmissionSerializer,
)
from .services import change_submission_status


class QuestionSetResponseSerializer(serializers.Serializer):
    version = serializers.CharField()
    title = serializers.CharField(required=False)
    subtitle = serializers.CharField(required=False)
    group_labels = serializers.DictField(child=serializers.CharField())
    sections = serializers.DictField(child=serializers.DictField(), required=False)
    cta = serializers.DictField(required=False)
    helper = serializers.DictField(required=False)
    share = serializers.DictField(required=False)
    non_selectable_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    groups = serializers.DictField(child=serializers.ListField(child=serializers.DictField()))
    required_ids = serializers.ListField(child=serializers.CharField(), required=False)


def _submission_examples():
    return [
        OpenApiExample(
            name="Submission payload",
            value={
                "title": "Midnight Track Build",
                "story_blocks": [
                    {
                        "question_id": "intro_1",
                        "answer": "트랙 레이스를 보고 시작했습니다.",
                        "images": [
                            "https://cdn.spokit.co/submissions/123/intro.jpg"
                        ]
                    },
                    {
                        "question_id": "final_1",
                        "answer": "밤을 가르는 한 줄기 빛",
                        "images": []
                    }
                ],
                "build_snapshot": {
                    "frame_brand": "Affinity",
                    "frame_name": "Midnight Run",
                },
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Submission response",
            value={
                "id": "b8d2f8ab-2d8a-4c97-b6c3-1b9f9d6fb112",
                "title": "Midnight Track Build",
                "story_blocks": [
                    {
                        "question_id": "intro_1",
                        "question_text": "픽시를 처음 타게 된 계기나, 이 문화에 끌리게 된 이유가 있나요?",
                        "answer": "트랙 레이스를 보고 시작했습니다.",
                        "images": ["https://cdn.spokit.co/submissions/123/intro.jpg"]
                    },
                    {
                        "question_id": "final_1",
                        "question_text": "마지막으로, 당신의 스포킷은 무엇인가요?",
                        "answer": "밤을 가르는 한 줄기 빛",
                        "images": []
                    }
                ],
                "build_snapshot": {
                    "frame_brand": "Affinity",
                    "frame_name": "Midnight Run",
                },
                "status": "submitted",
                "created_at": "2025-05-01T21:05:11Z",
                "updated_at": "2025-05-10T11:22:33Z",
            },
            response_only=True,
        ),
    ]


@extend_schema_view(
    list=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 목록 조회",
        examples=_submission_examples(),
    ),
    retrieve=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 상세 조회",
        examples=_submission_examples(),
    ),
    create=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 생성",
        examples=_submission_examples(),
    ),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 부분 수정",
        examples=_submission_examples(),
    ),
    destroy=extend_schema(tags=["Submissions"], summary="소개 신청 삭제"),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    """소개 신청서 CRUD를 제공하는 API."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).select_related("bike", "build").prefetch_related("images")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        """PUT 대신 PATCH 동작으로 통일합니다."""

        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Submissions"],
        summary="신청서 제출",
        description="초안 상태의 신청서를 접수 상태로 전환합니다.",
        request=None,
        responses=SubmissionSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        submission = self.get_object()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.SUBMITTED,
            actor=request.user,
        )
        return Response(
            SubmissionSerializer(submission, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Submissions"],
        summary="재신청",
        description="반려된 신청서를 수정 후 재신청합니다.",
        request=SubmissionCommentSerializer,
        responses=SubmissionSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def resubmit(self, request, pk=None):
        submission = self.get_object()
        payload = SubmissionCommentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        change_submission_status(
            submission,
            to_status=SubmissionStatus.RESUBMITTED,
            actor=request.user,
            comment=payload.validated_data.get("comment", ""),
        )
        return Response(
            SubmissionSerializer(submission, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class SubmissionModerationViewSet(viewsets.GenericViewSet):
    """운영진 전용 신청서 상태 전이 API."""

    queryset = Submission.objects.select_related("user", "bike", "build")
    serializer_class = SubmissionSerializer
    permission_classes = [IsStaffUser]
    http_method_names = ["post", "head", "options"]

    def get_serializer_context(self):  # 사용자 serializer와 동일한 context 제공
        context = super().get_serializer_context()
        request = getattr(self, "request", None)
        if request:
            context["request"] = request
        return context

    @extend_schema(
        tags=["Submission Moderation"],
        summary="검토 상태로 전환",
        description="운영진이 신청서를 검토중 상태로 전환합니다.",
        request=None,
        responses=SubmissionSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStaffUser])
    def review(self, request, pk=None):
        submission = self.get_object()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.IN_REVIEW,
            actor=request.user,
        )
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Submission Moderation"],
        summary="신청서 승인",
        description="에디터/관리자가 신청서를 승인 상태로 전환합니다.",
        request=None,
        responses=SubmissionSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[IsEditorOrAdmin])
    def approve(self, request, pk=None):
        submission = self.get_object()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.APPROVED,
            actor=request.user,
        )
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Submission Moderation"],
        summary="신청서 반려",
        description="운영진이 신청서를 반려하고 사유를 기록합니다.",
        request=SubmissionRejectSerializer,
        responses=SubmissionSerializer,
    )
    @action(detail=True, methods=["post"], permission_classes=[IsEditorOrAdmin])
    def reject(self, request, pk=None):
        submission = self.get_object()
        payload = SubmissionRejectSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        reason = payload.validated_data["reason"].strip()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.REJECTED,
            actor=request.user,
            comment=reason,
        )
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuestionSetView(APIView):
    """버전별 질문 세트를 내려줍니다."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Submissions"],
        summary="질문 세트 조회",
        responses=QuestionSetResponseSerializer,
        examples=[
            OpenApiExample(
                name="Question set",
                value={
                    "version": "v1_3",
                    "title": "Every Spoke Tells a Story",
                    "group_labels": {
                        "me": "It’s Me! · 자기소개",
                        "intro": "나와 픽시의 시작"
                    },
                    "groups": {
                        "me": [
                            {"id": "me_1", "text": "간단히 자신을 소개해주세요.", "required": True}
                        ],
                        "final": [
                            {
                                "id": "final_1",
                                "text": "마지막으로, 당신의 스포킷은 무엇인가요?",
                                "required": True
                            }
                        ]
                    },
                    "required_ids": ["me_1", "final_1"],
                    "non_selectable_groups": ["final", "me"],
                },
            )
        ],
    )
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
