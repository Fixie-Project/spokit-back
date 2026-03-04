"""Core-level utility API views (e.g., image upload/metadata registration)."""
from __future__ import annotations

import os
import re
from urllib.parse import quote
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Case, When, Value, IntegerField, Count, F, TextField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiExample
from PIL import Image
from rest_framework import permissions, status, views
from rest_framework.parsers import FormParser, MultiPartParser

from app.core.responses import error_response, success_response
from app.post.models import Post, PostImagePurpose, PostStatus
from app.user.models import User
from app.bike.models import BikeBuild
from app.core.serializers import (
    BaseImageUploadSerializer,
    BaseImageUploadResponseSerializer,
    BuildSearchSerializer,
    GlobalSearchMessageSerializer,
    HomeResponseSerializer,
    HomeBuildSerializer,
    HomePostSerializer,
    PostSearchSerializer,
    RiderSearchSerializer,
)

PUBLIC_TAG = "Public"

SEARCH_ALLOWED_TYPES = {"all", "magazine", "archive", "riders"}
SEARCH_ALLOWED_SORTS = {"relevance", "latest", "popular"}
SEARCH_DEFAULT_PREVIEW_LIMIT = 3
SEARCH_DEFAULT_PAGE_SIZE = 12
SEARCH_MAX_PAGE_SIZE = 24
SEARCH_MAX_PREVIEW_LIMIT = 10


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(number: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(number, max_value))


def _preview_with_has_more(qs, limit: int):
    items = list(qs[: limit + 1])
    has_more = len(items) > limit
    return items[:limit], has_more


def _paginate_with_has_more(qs, page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size
    items = list(qs[start : end + 1])
    has_more = len(items) > page_size
    return items[:page_size], has_more


def _apply_post_sort(qs, sort: str):
    if sort == "popular":
        return qs.order_by("-popularity", "-published_at", "-created_at")
    if sort == "latest":
        return qs.order_by("-published_at", "-created_at")
    return qs.order_by("-score", "-published_at", "-created_at")


def _apply_build_sort(qs, sort: str):
    if sort == "popular":
        return qs.order_by("-popularity", "-created_at")
    if sort == "latest":
        return qs.order_by("-created_at")
    return qs.order_by("-score", "-created_at")


def _apply_rider_sort(qs, sort: str):
    if sort == "latest":
        return qs.order_by("-created_at")
    return qs.order_by("-score", "-created_at")

def _build_word_regex(keyword: str) -> str:
    tokens = [re.escape(token) for token in re.split(r"\s+", keyword.strip()) if token]
    return r"\m(" + "|".join(tokens) + r")\M"


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
            image = Image.open(BytesIO(buffer))
            width, height = image.size
        except Exception:  # pragma: no cover - PIL 오류
            return error_response("이미지 파일을 읽을 수 없습니다.", status_code=status.HTTP_400_BAD_REQUEST)

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
        keyword = request.query_params.get("q", "").strip()
        if not keyword:
            return error_response("q 파라미터를 입력해 주세요.", status_code=status.HTTP_400_BAD_REQUEST)

        type_value = request.query_params.get("type", "all").strip().lower()
        sort_value = request.query_params.get("sort", "relevance").strip().lower()

        if type_value not in SEARCH_ALLOWED_TYPES:
            return error_response("type 파라미터가 올바르지 않습니다.", status_code=status.HTTP_400_BAD_REQUEST)
        if sort_value not in SEARCH_ALLOWED_SORTS:
            return error_response("sort 파라미터가 올바르지 않습니다.", status_code=status.HTTP_400_BAD_REQUEST)

        preview_limit = _clamp(
            _safe_int(request.query_params.get("preview_limit"), SEARCH_DEFAULT_PREVIEW_LIMIT),
            1,
            SEARCH_MAX_PREVIEW_LIMIT,
        )
        page = _clamp(_safe_int(request.query_params.get("page"), 1), 1, 10_000)
        page_size = _clamp(
            _safe_int(request.query_params.get("page_size"), SEARCH_DEFAULT_PAGE_SIZE),
            1,
            SEARCH_MAX_PAGE_SIZE,
        )
        query_encoded = quote(keyword)

        def _view_all_url(tab: str) -> str:
            return f"/search?q={query_encoded}&type={tab}&sort={sort_value}"

        # Posts (magazine)
        word_regex = _build_word_regex(keyword)

        post_base = (
            Post.objects.filter(status=PostStatus.PUBLISHED)
            .filter(
                models.Q(main_title__iregex=word_regex)
                | models.Q(sub_title__iregex=word_regex)
                | models.Q(content_md__iregex=word_regex)
                | models.Q(content_html__iregex=word_regex)
                | models.Q(tags__name__iregex=word_regex)
            )
            .distinct()
        )
        post_scored = post_base.annotate(
            score=(
                Case(
                    When(main_title__iregex=word_regex, then=Value(40)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(sub_title__iregex=word_regex, then=Value(25)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(content_md__iregex=word_regex, then=Value(10)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(content_html__iregex=word_regex, then=Value(5)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(tags__name__iregex=word_regex, then=Value(20)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        if sort_value == "popular":
            post_scored = post_scored.annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count("comments", distinct=True),
            ).annotate(
                popularity=F("like_count") + F("comment_count"),
            )
        post_qs = _apply_post_sort(post_scored, sort_value).prefetch_related("images", "tags")

        # Riders (users)
        rider_base = (
            User.objects.filter(is_active=True)
            .filter(
                models.Q(username__iregex=word_regex)
                | models.Q(region__iregex=word_regex)
                | models.Q(intro__iregex=word_regex)
            )
        )
        rider_scored = rider_base.annotate(
            score=(
                Case(
                    When(username__iregex=word_regex, then=Value(30)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(region__iregex=word_regex, then=Value(20)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(intro__iregex=word_regex, then=Value(10)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        rider_qs = _apply_rider_sort(rider_scored, sort_value).select_related("profile_image")

        # Builds (archive)
        build_base = (
            BikeBuild.objects.filter(is_public=True)
            .annotate(components_text=Cast("components", TextField()))
            .filter(
                models.Q(base_bike__frame_name__iregex=word_regex)
                | models.Q(components_text__iregex=word_regex)
            )
        )
        build_scored = build_base.annotate(
            score=(
                Case(
                    When(base_bike__frame_name__iregex=word_regex, then=Value(30)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                + Case(
                    When(components_text__iregex=word_regex, then=Value(20)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        if sort_value == "popular":
            build_scored = build_scored.annotate(
                popularity=Count("likes", distinct=True),
            )
        build_qs = _apply_build_sort(build_scored, sort_value).select_related("base_bike", "main_image")

        if type_value == "all":
            post_preview, post_has_more = _preview_with_has_more(post_qs, preview_limit)
            rider_preview, rider_has_more = _preview_with_has_more(rider_qs, preview_limit)
            build_preview, build_has_more = _preview_with_has_more(build_qs, preview_limit)

            payload = {
                "query": keyword,
                "type": "all",
                "sort": sort_value,
                "groups": {
                            "magazine": {
                                "items": PostSearchSerializer(
                                    post_preview,
                                    many=True,
                                    context={"search_keyword": keyword},
                                ).data,
                                "has_more": post_has_more,
                                "view_all_url": _view_all_url("magazine"),
                            },
                            "archive": {
                                "items": BuildSearchSerializer(
                                    build_preview,
                                    many=True,
                                    context={"search_keyword": keyword},
                                ).data,
                                "has_more": build_has_more,
                                "view_all_url": _view_all_url("archive"),
                            },
                            "riders": {
                                "items": RiderSearchSerializer(rider_preview, many=True).data,
                        "has_more": rider_has_more,
                        "view_all_url": _view_all_url("riders"),
                    },
                },
            }
            return success_response("검색 결과를 조회했습니다.", payload)

        if type_value == "magazine":
            items, has_more = _paginate_with_has_more(post_qs, page, page_size)
            payload = {
                "query": keyword,
                "type": "magazine",
                "sort": sort_value,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "items": PostSearchSerializer(
                    items,
                    many=True,
                    context={"search_keyword": keyword},
                ).data,
            }
            return success_response("검색 결과를 조회했습니다.", payload)

        if type_value == "archive":
            items, has_more = _paginate_with_has_more(build_qs, page, page_size)
            payload = {
                "query": keyword,
                "type": "archive",
                "sort": sort_value,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "items": BuildSearchSerializer(
                    items,
                    many=True,
                    context={"search_keyword": keyword},
                ).data,
            }
            return success_response("검색 결과를 조회했습니다.", payload)

        if type_value == "riders":
            items, has_more = _paginate_with_has_more(rider_qs, page, page_size)
            payload = {
                "query": keyword,
                "type": "riders",
                "sort": sort_value,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "items": RiderSearchSerializer(items, many=True).data,
            }
            return success_response("검색 결과를 조회했습니다.", payload)

        return error_response("요청을 처리할 수 없습니다.", status_code=status.HTTP_400_BAD_REQUEST)


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
