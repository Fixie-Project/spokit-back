"""공통 페이지네이션 설정."""
from __future__ import annotations

from rest_framework.pagination import LimitOffsetPagination


class PostLimitOffsetPagination(LimitOffsetPagination):
    """포스트 목록 기본 페이지네이션."""

    default_limit = 9
    max_limit = 30


class BuildLimitOffsetPagination(LimitOffsetPagination):
    """빌드(아카이브) 목록 기본 페이지네이션."""

    default_limit = 10
    max_limit = 50
