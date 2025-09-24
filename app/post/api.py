"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from .models import Post
from .serializers import PostSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Posts"],
        summary="게시글 목록 조회",
        description="발행된 게시글 목록을 반환합니다. 관리자는 모든 상태의 게시글을 확인할 수 있습니다.",
    ),
    retrieve=extend_schema(
        tags=["Posts"],
        summary="특정 게시글 조회",
        description="게시글 상세 정보를 반환합니다. 비회원은 발행된 게시글만 조회할 수 있습니다.",
    ),
)
class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """게시글 목록/상세 조회 API."""

    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    queryset = (
        Post.objects.select_related("author")
        .prefetch_related("tags", "likes", "source_submissions")
        .all()
    )

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(status="published")
        return qs
