"""Search utilities for core API."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

from django.db import connection, models
from django.db.models import Case, When, Value, IntegerField, Count, F, TextField
from django.db.models.functions import Cast

from app.post.models import Post, PostStatus
from app.user.models import User
from app.bike.models import BikeBuild
from app.core.serializers import PostSearchSerializer, RiderSearchSerializer, BuildSearchSerializer


SEARCH_ALLOWED_TYPES = {"all", "magazine", "archive", "riders"}
SEARCH_ALLOWED_SORTS = {"relevance", "latest", "popular"}
SEARCH_DEFAULT_PREVIEW_LIMIT = 3
SEARCH_DEFAULT_PAGE_SIZE = 12
SEARCH_MAX_PAGE_SIZE = 24
SEARCH_MAX_PREVIEW_LIMIT = 10


class SearchError(ValueError):
    """Raised when search params are invalid."""


@dataclass(frozen=True)
class SearchParams:
    query: str
    type_value: str
    sort_value: str
    preview_limit: int
    page: int
    page_size: int


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
    if not tokens:
        return r"$^"
    # PostgreSQL word boundary uses \m \M, SQLite uses Python re so \b is safer.
    if connection.vendor == "postgresql":
        start, end = r"\m", r"\M"
    else:
        start, end = r"\b", r"\b"
    return f"{start}(" + "|".join(tokens) + f"){end}"


class IRegexSearchEngine:
    """Search engine using iregex matching."""

    def post_queryset(self, keyword: str, sort_value: str):
        word_regex = _build_word_regex(keyword)
        base = (
            Post.objects.filter(status=PostStatus.PUBLISHED)
            .filter(
                models.Q(main_title__iregex=word_regex)
                | models.Q(content_md__iregex=word_regex)
                | models.Q(content_html__iregex=word_regex)
                | models.Q(tags__name__iregex=word_regex)
            )
            .distinct()
        )
        scored = base.annotate(
            score=(
                Case(
                    When(main_title__iregex=word_regex, then=Value(40)),
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
            scored = scored.annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count("comments", distinct=True),
            ).annotate(
                popularity=F("like_count") + F("comment_count"),
            )
        return _apply_post_sort(scored, sort_value).prefetch_related("images", "tags")

    def rider_queryset(self, keyword: str, sort_value: str):
        word_regex = _build_word_regex(keyword)
        base = (
            User.objects.filter(is_active=True)
            .filter(
                models.Q(username__iregex=word_regex)
                | models.Q(region__iregex=word_regex)
                | models.Q(intro__iregex=word_regex)
            )
        )
        scored = base.annotate(
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
        return _apply_rider_sort(scored, sort_value).select_related("profile_image")

    def build_queryset(self, keyword: str, sort_value: str):
        word_regex = _build_word_regex(keyword)
        base = (
            BikeBuild.objects.filter(is_public=True)
            .annotate(components_text=Cast("components", TextField()))
            .filter(
                models.Q(base_bike__frame_name__iregex=word_regex)
                | models.Q(components_text__iregex=word_regex)
            )
        )
        scored = base.annotate(
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
            scored = scored.annotate(popularity=Count("likes", distinct=True))
        return _apply_build_sort(scored, sort_value).select_related("base_bike", "main_image")


class SearchService:
    """Search service with pluggable engine."""

    def __init__(self, engine: IRegexSearchEngine | None = None):
        self.engine = engine or IRegexSearchEngine()

    def parse_params(self, query_params) -> SearchParams:
        keyword = query_params.get("q", "").strip()
        if not keyword:
            raise SearchError("q 파라미터를 입력해 주세요.")

        type_value = query_params.get("type", "all").strip().lower()
        sort_value = query_params.get("sort", "relevance").strip().lower()

        if type_value not in SEARCH_ALLOWED_TYPES:
            raise SearchError("type 파라미터가 올바르지 않습니다.")
        if sort_value not in SEARCH_ALLOWED_SORTS:
            raise SearchError("sort 파라미터가 올바르지 않습니다.")

        preview_limit = _clamp(
            _safe_int(query_params.get("preview_limit"), SEARCH_DEFAULT_PREVIEW_LIMIT),
            1,
            SEARCH_MAX_PREVIEW_LIMIT,
        )
        page = _clamp(_safe_int(query_params.get("page"), 1), 1, 10_000)
        page_size = _clamp(
            _safe_int(query_params.get("page_size"), SEARCH_DEFAULT_PAGE_SIZE),
            1,
            SEARCH_MAX_PAGE_SIZE,
        )
        return SearchParams(
            query=keyword,
            type_value=type_value,
            sort_value=sort_value,
            preview_limit=preview_limit,
            page=page,
            page_size=page_size,
        )

    def search(self, query_params) -> dict:
        params = self.parse_params(query_params)
        post_qs = self.engine.post_queryset(params.query, params.sort_value)
        rider_qs = self.engine.rider_queryset(params.query, params.sort_value)
        build_qs = self.engine.build_queryset(params.query, params.sort_value)

        def _view_all_url(tab: str) -> str:
            q_encoded = quote(params.query)
            return f"/search?q={q_encoded}&type={tab}&sort={params.sort_value}"

        if params.type_value == "all":
            post_preview, post_has_more = _preview_with_has_more(post_qs, params.preview_limit)
            rider_preview, rider_has_more = _preview_with_has_more(rider_qs, params.preview_limit)
            build_preview, build_has_more = _preview_with_has_more(build_qs, params.preview_limit)
            return {
                "query": params.query,
                "type": "all",
                "sort": params.sort_value,
                "groups": {
                    "magazine": {
                        "items": PostSearchSerializer(
                            post_preview,
                            many=True,
                            context={"search_keyword": params.query},
                        ).data,
                        "has_more": post_has_more,
                        "view_all_url": _view_all_url("magazine"),
                    },
                    "archive": {
                        "items": BuildSearchSerializer(
                            build_preview,
                            many=True,
                            context={"search_keyword": params.query},
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

        if params.type_value == "magazine":
            items, has_more = _paginate_with_has_more(post_qs, params.page, params.page_size)
            return {
                "query": params.query,
                "type": "magazine",
                "sort": params.sort_value,
                "page": params.page,
                "page_size": params.page_size,
                "has_more": has_more,
                "items": PostSearchSerializer(
                    items,
                    many=True,
                    context={"search_keyword": params.query},
                ).data,
            }

        if params.type_value == "archive":
            items, has_more = _paginate_with_has_more(build_qs, params.page, params.page_size)
            return {
                "query": params.query,
                "type": "archive",
                "sort": params.sort_value,
                "page": params.page,
                "page_size": params.page_size,
                "has_more": has_more,
                "items": BuildSearchSerializer(
                    items,
                    many=True,
                    context={"search_keyword": params.query},
                ).data,
            }

        if params.type_value == "riders":
            items, has_more = _paginate_with_has_more(rider_qs, params.page, params.page_size)
            return {
                "query": params.query,
                "type": "riders",
                "sort": params.sort_value,
                "page": params.page,
                "page_size": params.page_size,
                "has_more": has_more,
                "items": RiderSearchSerializer(items, many=True).data,
            }

        raise SearchError("요청을 처리할 수 없습니다.")
