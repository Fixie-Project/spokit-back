"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from django.db.models import Count, F, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework import mixins, permissions, viewsets
from app.core.pagination import PostLimitOffsetPagination
from app.core.responses import success_response
from .models import Post, PostStatus
from .serializers import (
    PostDetailResponseSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostListResponseSerializer,
    PostSerializer,
)

PUBLIC_TAG = "Public"


@extend_schema_view(
    list=extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="게시글 목록 조회",
        description="발행된 게시글 목록을 반환합니다. 관리자는 모든 상태의 게시글을 확인할 수 있습니다.",
        responses=PostListResponseSerializer,
    ),
    retrieve=extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="특정 게시글 조회",
        description="게시글 상세 정보를 반환합니다. 비회원은 발행된 게시글만 조회할 수 있습니다.",
        responses=PostDetailResponseSerializer,
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
    pagination_class = PostLimitOffsetPagination
    queryset = (
        Post.objects.select_related("author__user", "submission", "bike", "build", "rider")
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
        return success_response("게시글을 조회했습니다.", serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            payload = {
                "count": self.paginator.count,
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": serializer.data,
            }
            return success_response("게시글 목록을 조회했습니다.", payload)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            "게시글 목록을 조회했습니다.",
            {"count": queryset.count(), "results": serializer.data},
        )

    @extend_schema(
        tags=["Posts", PUBLIC_TAG],
        summary="인기 게시글 TOP3",
        description="좋아요 수 + 댓글 수를 기준으로 상위 3개 발행 게시글을 반환합니다.",
        responses=PostListResponseSerializer,
    )
    @action(detail=False, methods=["get"], url_path="popular", permission_classes=[permissions.AllowAny])
    def popular(self, request, *args, **kwargs):
        queryset = (
            self.get_queryset()
            .annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count("comments", distinct=True),
            )
            .prefetch_related("images")
            .order_by("-like_count", "-comment_count", "-created_at")[:3]
        )
        serializer = PostListSerializer(queryset, many=True, context={"request": request})
        return success_response(
            "인기 게시글을 조회했습니다.",
            {"count": len(serializer.data), "results": serializer.data},
        )
