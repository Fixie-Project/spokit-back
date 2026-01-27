"""사용자 인증 및 마이페이지 관련 API 뷰."""
from __future__ import annotations

import re

from django.conf import settings
from django.db.models import Count
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import exceptions, permissions, status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from app.core.responses import success_response
from app.submission.models import Submission, SubmissionStatus

from .models import User, UserRole
from .serializers import (
    EmailTokenObtainPairSerializer,
    GoogleOAuthSerializer,
    PublicUserProfileSerializer,
    UserProfileSerializer,
)

PUBLIC_TAG = "Public"


class UserProfileSummaryAPIView(views.APIView):
    """신청 상태별 통계 요약을 제공합니다."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        submissions = Submission.objects.filter(user=request.user)
        totals_by_status = {status: 0 for status in SubmissionStatus.values}
        for row in submissions.values("status").annotate(count=Count("status")):
            totals_by_status[row["status"]] = row["count"]

        stats = {"total": submissions.count(), "by_status": totals_by_status}
        return success_response("신청 상태 요약을 조회했습니다.", stats)


class UserProfileAPIView(views.APIView):
    """사용자 프로필 조회 및 수정."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=UserProfileSerializer,
        tags=["User"],
        summary="내 프로필 조회",
        examples=[
            OpenApiExample(
                "응답 예시",
                value={
                    "message": "프로필을 조회했습니다.",
                    "data": {
                        "id": "a9a5f50e-6f82-4b65-8d2b-fc36bd2f2c1d",
                        "email": "user@example.com",
                        "username": "spokit_user",
                        "is_username_public": False,
                        "nickname": "스포킷",
                        "region": "Seoul",
                        "intro": "트랙바이크 타는 라이더입니다.",
                        "sns_link": "https://instagram.com/spokit",
                        "profile_image": None,
                    },
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request) -> Response:
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return success_response("프로필을 조회했습니다.", serializer.data)

    @extend_schema(
        request=UserProfileSerializer,
        responses=UserProfileSerializer,
        tags=["User"],
        summary="내 프로필 수정",
        examples=[
            OpenApiExample(
                "요청 예시",
                value={
                    "nickname": "새닉네임",
                    "region": "Seoul",
                    "intro": "트랙바이크 타는 라이더입니다.",
                    "sns_link": "https://instagram.com/spokit",
                },
                request_only=True,
            ),
            OpenApiExample(
                "응답 예시",
                value={
                    "message": "프로필을 수정했습니다.",
                    "data": {
                        "id": "a9a5f50e-6f82-4b65-8d2b-fc36bd2f2c1d",
                        "email": "user@example.com",
                        "username": "spokit_user",
                        "is_username_public": False,
                        "nickname": "새닉네임",
                        "region": "Seoul",
                        "intro": "트랙바이크 타는 라이더입니다.",
                        "sns_link": "https://instagram.com/spokit",
                        "profile_image": None,
                    },
                },
                response_only=True,
            ),
        ],
    )
    def patch(self, request) -> Response:
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("프로필을 수정했습니다.", serializer.data)


class EmailTokenObtainPairAPIView(TokenObtainPairView):
    """이메일·비밀번호 기반 JWT 발급 뷰."""

    serializer_class = EmailTokenObtainPairSerializer


class PublicUserProfileAPIView(views.APIView):
    """공개 사용자 프로필 조회."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["User", PUBLIC_TAG],
        summary="사용자 공개 프로필",
        responses=PublicUserProfileSerializer,
    )
    def get(self, request, user_id: str) -> Response:
        user = get_object_or_404(get_user_model(), id=user_id, is_active=True)
        serializer = PublicUserProfileSerializer(user, context={"request": request})
        return success_response("사용자 프로필을 조회했습니다.", serializer.data)


class GoogleOAuthLoginAPIView(views.APIView):
    """구글 OAuth id_token을 검증하여 JWT를 발급."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["User", PUBLIC_TAG],
        summary="Google OAuth 로그인",
        request=GoogleOAuthSerializer,
    )
    def post(self, request, *args, **kwargs) -> Response:
        serializer = GoogleOAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_value = serializer.validated_data["id_token"]

        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            from google.auth.exceptions import GoogleAuthError
        except ImportError as exc:  # pragma: no cover - 환경 의존
            raise exceptions.APIException("google-auth 라이브러리가 설치되어 있지 않습니다.") from exc

        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        if not client_id:
            raise exceptions.AuthenticationFailed("구글 OAuth 클라이언트 ID가 설정되어 있지 않습니다.")

        try:
            id_info = google_id_token.verify_oauth2_token(
                id_token_value,
                google_requests.Request(),
                client_id,
            )
        except GoogleAuthError as exc:
            raise exceptions.AuthenticationFailed("유효하지 않은 Google id_token 입니다.") from exc
        except ValueError as exc:  # pragma: no cover - 검증 실패
            raise exceptions.AuthenticationFailed("id_token 검증에 실패했습니다.") from exc

        email = id_info.get("email")
        if not email:
            raise exceptions.AuthenticationFailed("Google 프로필에서 이메일을 확인할 수 없습니다.")

        nickname = id_info.get("name") or email.split("@")[0]
        nickname = self._generate_unique_nickname(nickname)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": nickname,
                "nickname": nickname,
                "role": UserRole.USER,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        refresh = RefreshToken.for_user(user)
        refresh["nickname"] = user.nickname
        refresh["role"] = user.role

        access_token = refresh.access_token
        access_token["nickname"] = user.nickname
        access_token["role"] = user.role

        return success_response(
            "로그인에 성공했습니다.",
            {
                "refresh": str(refresh),
                "access": str(access_token),
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "is_new": created,
            },
            status_code=status.HTTP_200_OK,
        )

    def _generate_unique_nickname(self, base: str) -> str:
        """닉네임 중복을 피하도록 고유 값을 생성."""

        base_candidate = re.sub(r"[^\w가-힣]+", "", base).strip() or "spokit"
        candidate = base_candidate
        counter = 1
        while User.objects.filter(nickname=candidate).exists():
            counter += 1
            candidate = f"{base_candidate}{counter}"
        return candidate
