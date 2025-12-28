"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from django.db.models import Count, F, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response

from .models import Post, PostStatus
from .serializers import (
    PostDetailSerializer,
    PostListSerializer,
    PostSerializer,
)

PUBLIC_TAG = "Public"


@extend_schema_view(
    list=extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="게시글 목록 조회",
        description="발행된 게시글 목록을 반환합니다. 관리자는 모든 상태의 게시글을 확인할 수 있습니다.",
    ),
    retrieve=extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="특정 게시글 조회",
        description="게시글 상세 정보를 반환합니다. 비회원은 발행된 게시글만 조회할 수 있습니다.",
    ),
)
class PostViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """게시글 목록/상세 API (작성·수정·삭제는 Studio 전용)."""

    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = (
        Post.objects.select_related("author", "submission", "bike", "build", "rider")
        .prefetch_related("tags", "likes", "images")
        .annotate(comment_count=Count("comments", distinct=True))
    )

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(status=PostStatus.PUBLISHED)
        query = self.request.query_params.get("q")
        if query:
            qs = qs.filter(
                Q(main_title__icontains=query)
                | Q(sub_title__icontains=query)
                | Q(content_md__icontains=query)
                | Q(frame_brand__icontains=query)
            )
        return qs

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status == PostStatus.PUBLISHED:
            Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
            post.view_count += 1
        serializer = self.get_serializer(post)
        return Response(serializer.data)
