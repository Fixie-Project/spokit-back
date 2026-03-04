"""Core-level utility API views (e.g., image upload/metadata registration)."""
from __future__ import annotations

import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions, status, views
from rest_framework.parsers import FormParser, MultiPartParser

from app.core.responses import error_response, success_response
from app.core.models import BaseImage
from app.post.models import Post, PostStatus
from app.core.serializers import (
    BaseImageUploadSerializer,
    BaseImageUploadResponseSerializer,
    GlobalSearchMessageSerializer,
    HomeResponseSerializer,
    HomeBuildSerializer,
    HomePostSerializer,
)
from app.core.images import verify_image_upload
from app.core.search import SearchService, SearchError

PUBLIC_TAG = "Public"


class BaseImageUploadView(views.APIView):
    """Register an already-uploaded image (e.g., S3) as BaseImage."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Images"],
        summary="이미지 메타데이터 등록",
        description="S3 등에 업로드된 이미지의 메타데이터(url, s3_key 등)를 등록하고 id를 반환합니다.",
        request=BaseImageUploadSerializer,
        responses=BaseImageUploadResponseSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = BaseImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            "이미지 메타데이터를 등록했습니다.",
            serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class BaseImageFileUploadView(views.APIView):
    """파일 업로드를 받아 S3(기본 스토리지)에 저장 후 BaseImage를 생성합니다."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    max_filesize = 10 * 1024 * 1024  # 10 MB
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    @extend_schema(
        tags=["Images"],
        summary="이미지 파일 업로드",
        description="multipart/form-data로 파일을 업로드하고 BaseImage 메타를 반환합니다.",
        responses=BaseImageUploadResponseSerializer,
    )
    def post(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        if not upload:
            return error_response("파일을 첨부해 주세요.", status_code=status.HTTP_400_BAD_REQUEST)

        if upload.size > self.max_filesize:
            return error_response("최대 10MB까지 업로드할 수 있습니다.", status_code=status.HTTP_400_BAD_REQUEST)

        ext = (os.path.splitext(upload.name)[1] or "").lower().lstrip(".")
        if ext not in self.allowed_extensions:
            return error_response("허용되지 않은 파일 형식입니다.", status_code=status.HTTP_400_BAD_REQUEST)

        # 추출을 위해 읽고, 저장은 별도 버퍼로 처리
        buffer = upload.read()
        try:
            width, height = verify_image_upload(buffer)
        except ValueError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        saved_name = default_storage.save(upload.name, ContentFile(buffer))
        url = default_storage.url(saved_name)

        obj = BaseImage.objects.create(
            url=url,
            s3_key=saved_name,
            width=width,
            height=height,
            filesize=upload.size,
        )
        return success_response(
            "이미지 파일을 업로드했습니다.",
            BaseImageUploadSerializer(obj).data,
            status_code=status.HTTP_201_CREATED,
        )


@method_decorator(cache_page(60), name="dispatch")
class GlobalSearchAPIView(views.APIView):
    """메거진/라이더/아카이브 통합 검색."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Search", PUBLIC_TAG],
        summary="통합 검색 (메거진/라이더/아카이브)",
        parameters=[],
        responses=GlobalSearchMessageSerializer,
        examples=[
            OpenApiExample(
                "Search response",
                value={
                    "message": "검색 결과를 조회했습니다.",
                    "data": {
                        "query": "cinelli",
                        "type": "all",
                        "sort": "relevance",
                        "groups": {
                            "magazine": {
                                "items": [
                                    {
                                        "id": "uuid",
                                        "slug": "chrome-dreams",
                                        "main_title": "Chrome Dreams",
                                        "sub_title": "Cinelli Mash Histogram",
                                        "is_editor_pick": False,
                                        "image": {"url": "https://.../hero.jpg", "purpose": "header"},
                                        "tags": [{"id": "uuid", "name": "fixed-gear"}],
                                        "matched_excerpt": "...Cinelli Mash Histogram...",
                                    }
                                ],
                                "has_more": True,
                                "view_all_url": "/search?q=cinelli&type=magazine&sort=relevance",
                            },
                            "archive": {
                                "items": [
                                    {
                                        "id": "uuid",
                                        "title": "Neon Nights",
                                        "main_image": {"url": "https://.../main.jpg", "width": 800, "height": 600},
                                        "matched_components": ["Phil Wood hub", "H Plus Son rim"],
                                    }
                                ],
                                "has_more": False,
                                "view_all_url": "/search?q=cinelli&type=archive&sort=relevance",
                            },
                            "riders": {
                                "items": [
                                    {
                                        "id": "uuid",
                                        "username": "spokit_rider",
                                        "location": "Seoul",
                                        "bio": "서울 기반 픽서",
                                        "profile_image": {"url": "https://.../profile.jpg", "width": 400, "height": 400},
                                    }
                                ],
                                "has_more": False,
                                "view_all_url": "/search?q=cinelli&type=riders&sort=relevance",
                            },
                        },
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        service = SearchService()
        try:
            payload = service.search(request.query_params)
        except SearchError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        return success_response("검색 결과를 조회했습니다.", payload)


@method_decorator(cache_page(60), name="dispatch")
class HomeAPIView(views.APIView):
    """홈 화면용 인기 글/최신 빌드 요약."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Home", PUBLIC_TAG],
        summary="홈 데이터 조회",
        responses=HomeResponseSerializer,
        examples=[
            OpenApiExample(
                "Home response",
                value={
                    "message": "홈 데이터를 조회했습니다.",
                    "data": {
                        "posts": [
                            {
                                "id": "uuid",
                                "slug": "chrome-dreams",
                                "main_title": "Chrome Dreams",
                                "sub_title": "Cinelli Mash Histogram",
                                "created_at": "2025-01-01T12:00:00Z",
                                "is_editor_pick": False,
                                "image": {"url": "https://.../hero.jpg", "purpose": "thumbnail"},
                            }
                        ],
                        # "builds": [
                        #     {
                        #         "id": "uuid",
                        #         "title": "Neon Nights",
                        #         "bike_frame": "Cinelli Tutto Plus",
                        #         "is_public": True,
                        #         "main_image": {"url": "https://.../main.jpg", "width": 800, "height": 600},
                        #         "rider": {"id": "user-uuid", "name": "스포킷 라이더"},
                        #     }
                        # ],
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        # 기존 로직(인기글 상위 3 + 최신 빌드 10)
        # posts = (
        #     Post.objects.filter(status=PostStatus.PUBLISHED)
        #     .annotate(
        #         like_count=models.Count("likes", distinct=True),
        #         comment_count=models.Count("comments", distinct=True),
        #     )
        #     .prefetch_related("images")
        #     .order_by("-like_count", "-comment_count", "-created_at")[:3]
        # )
        # builds = (
        #     BikeBuild.objects.filter(is_public=True)
        #     .select_related("base_bike__owner", "main_image")
        #     .order_by("-created_at")[:10]
        # )
        # payload = {
        #     "posts": HomePostSerializer(posts, many=True).data,
        #     "builds": HomeBuildSerializer(builds, many=True).data,
        # }

        # 변경: 최신 글 4개만 반환
        latest_posts = (
            Post.objects.filter(status=PostStatus.PUBLISHED)
            .prefetch_related("images")
            .order_by("-created_at")[:4]
        )
        payload = {
            "posts": HomePostSerializer(latest_posts, many=True).data,
            # "builds": HomeBuildSerializer(builds, many=True).data,  # 최신 빌드 제거
        }
        return success_response("홈 데이터를 조회했습니다.", payload)
