"""소개 신청 관련 API 뷰셋 및 유틸 뷰."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView

from app.core.responses import error_response, success_response
from app.user.permissions import IsEditorOrAdmin, IsStaffUser

from .models import Submission, SubmissionStatus
from .questions import DEFAULT_QUESTION_VERSION, load_question_set
from .serializers import (
    QuestionSetMessageSerializer,
    SubmissionCommentSerializer,
    SubmissionDetailResponseSerializer,
    SubmissionListResponseSerializer,
    SubmissionRejectSerializer,
    SubmissionSerializer,
)
from .services import change_submission_status, ensure_post_for_submission

PUBLIC_TAG = "Public"

EDITABLE_STATUSES = {SubmissionStatus.DRAFT, SubmissionStatus.REJECTED}
DELETABLE_STATUSES = {SubmissionStatus.DRAFT, SubmissionStatus.REJECTED}

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
                    "frame_name": "Midnight Run",
                },
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Submission response",
            value={
                "message": "신청서를 조회했습니다.",
                "data": {
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
                        "frame_name": "Midnight Run",
                    },
                    "status": "submitted",
                    "reason_code": None,
                    "reason_detail": "",
                    "created_at": "2025-05-01T21:05:11Z",
                    "updated_at": "2025-05-10T11:22:33Z",
                },
            },
            response_only=True,
        ),
    ]


@extend_schema_view(
    list=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 목록 조회",
        examples=_submission_examples(),
        responses=SubmissionListResponseSerializer,
    ),
    retrieve=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 상세 조회",
        examples=_submission_examples(),
        responses=SubmissionDetailResponseSerializer,
    ),
    create=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 생성",
        examples=_submission_examples(),
        responses=SubmissionDetailResponseSerializer,
    ),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(
        tags=["Submissions"],
        summary="소개 신청 부분 수정",
        examples=_submission_examples(),
        responses=SubmissionDetailResponseSerializer,
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            "신청서를 조회했습니다.",
            {"count": queryset.count(), "results": serializer.data},
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response("신청서를 조회했습니다.", serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            "신청서를 등록했습니다.",
            serializer.data,
            status_code=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status not in EDITABLE_STATUSES:
            return error_response(
                "초안(draft) 또는 반려(rejected) 상태에서만 수정할 수 있습니다. 다른 상태는 관리자에게 문의해 주세요.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_STATUS",
            )
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response("신청서를 수정했습니다.", serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status not in DELETABLE_STATUSES:
            return error_response(
                "초안(draft) 또는 반려(rejected) 상태에서만 삭제할 수 있습니다. 다른 상태는 관리자에게 문의해 주세요.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_STATUS",
            )
        self.perform_destroy(instance)
        return success_response("신청서를 삭제했습니다.")

    @extend_schema(
        tags=["Submissions"],
        summary="신청서 제출",
        description="초안 상태의 신청서를 접수 상태로 전환합니다.",
        request=None,
        responses=SubmissionDetailResponseSerializer,
        examples=[
            OpenApiExample(
                "Submit response",
                value={
                    "message": "신청서를 접수 상태로 전환했습니다.",
                    "data": {"id": "uuid", "status": "submitted"},
                },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        submission = self.get_object()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.SUBMITTED,
            actor=request.user,
        )
        return success_response(
            "신청서를 접수 상태로 전환했습니다.",
            SubmissionSerializer(submission, context={"request": request}).data,
        )

    @extend_schema(
        tags=["Submissions"],
        summary="재신청",
        description="반려된 신청서를 수정 후 재신청합니다.",
        request=SubmissionCommentSerializer,
        responses=SubmissionDetailResponseSerializer,
        examples=[
            OpenApiExample(
                "Resubmit response",
                value={
                    "message": "신청서를 재접수했습니다.",
                    "data": {"id": "uuid", "status": "resubmitted"},
                },
                response_only=True,
            )
        ],
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
        return success_response(
            "신청서를 재접수했습니다.",
            SubmissionSerializer(submission, context={"request": request}).data,
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
        responses=SubmissionDetailResponseSerializer,
        examples=[
            OpenApiExample(
                "Review response",
                value={
                    "message": "신청서를 검토 상태로 전환했습니다.",
                    "data": {"id": "uuid", "status": "in_review"},
                },
                response_only=True,
            )
        ],
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
        return success_response("신청서를 검토 상태로 전환했습니다.", serializer.data)

    @extend_schema(
        tags=["Submission Moderation"],
        summary="신청서 승인",
        description="에디터/관리자가 신청서를 승인 상태로 전환합니다.",
        request=None,
        responses=SubmissionDetailResponseSerializer,
        examples=[
            OpenApiExample(
                "Approve response",
                value={
                    "message": "신청서를 승인했습니다.",
                    "data": {"id": "uuid", "status": "approved"},
                },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], permission_classes=[IsEditorOrAdmin])
    def approve(self, request, pk=None):
        submission = self.get_object()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.APPROVED,
            actor=request.user,
        )
        ensure_post_for_submission(submission, actor=request.user)
        serializer = self.get_serializer(submission)
        return success_response("신청서를 승인했습니다.", serializer.data)

    @extend_schema(
        tags=["Submission Moderation"],
        summary="신청서 반려",
        description="운영진이 신청서를 반려하고 사유를 기록합니다.",
        request=SubmissionRejectSerializer,
        responses=SubmissionDetailResponseSerializer,
        examples=[
            OpenApiExample(
                "Reject response",
                value={
                    "message": "신청서를 반려했습니다.",
                    "data": {
                        "id": "uuid",
                        "status": "rejected",
                        "reason_code": "photo_issue",
                        "reason_detail": "이미지 해상도가 낮습니다.",
                    },
                },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], permission_classes=[IsEditorOrAdmin])
    def reject(self, request, pk=None):
        submission = self.get_object()
        payload = SubmissionRejectSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        reason_code = payload.validated_data["reason_code"]
        reason_detail = payload.validated_data.get("reason_detail", "").strip()
        change_submission_status(
            submission,
            to_status=SubmissionStatus.REJECTED,
            actor=request.user,
            comment=reason_detail,
            reason_code=reason_code,
            reason_detail=reason_detail,
        )
        serializer = self.get_serializer(submission)
        return success_response("신청서를 반려했습니다.", serializer.data)


class QuestionSetView(APIView):
    """버전별 질문 세트를 내려줍니다."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Submissions", PUBLIC_TAG],
        summary="질문 세트 조회",
        responses=QuestionSetMessageSerializer,
        examples=[
            OpenApiExample(
                name="Question set",
                value={
                    "message": "질문 세트를 조회했습니다.",
                    "data": {
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
        return success_response("질문 세트를 조회했습니다.", payload)


class UserSubmissionListAPIView(APIView):
    """로그인 사용자의 신청 목록을 반환합니다."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Submissions"],
        summary="내 신청 목록 조회",
        responses=SubmissionListResponseSerializer,
    )
    def get(self, request):
        submissions = (
            Submission.objects.filter(user=request.user)
            .select_related("bike", "build")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        serializer = SubmissionSerializer(submissions, many=True, context={"request": request})
        return success_response(
            "신청서를 조회했습니다.",
            {
                "count": submissions.count(),
                "results": serializer.data,
            },
        )


class UserSubmissionDetailAPIView(APIView):
    """로그인 사용자의 개별 신청 조회/수정."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Submissions"], summary="내 신청 상세", responses=SubmissionDetailResponseSerializer)
    def get(self, request, pk: str):
        submission = get_object_or_404(Submission, pk=pk, user=request.user)
        serializer = SubmissionSerializer(submission, context={"request": request})
        return success_response("신청서를 조회했습니다.", serializer.data)

    @extend_schema(tags=["Submissions"], summary="내 신청 수정", responses=SubmissionDetailResponseSerializer)
    def patch(self, request, pk: str):
        submission = get_object_or_404(Submission, pk=pk, user=request.user)
        if submission.status not in EDITABLE_STATUSES:
            return error_response(
                "초안(draft) 또는 반려(rejected) 상태에서만 수정할 수 있습니다. 다른 상태는 관리자에게 문의해 주세요.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_STATUS",
            )
        serializer = SubmissionSerializer(
            submission,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("신청서를 수정했습니다.", serializer.data)
