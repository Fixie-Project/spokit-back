"""게시글 관련 API 뷰셋입니다."""
from __future__ import annotations

from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework import mixins, permissions, serializers, status, viewsets, views
from app.core.pagination import PostLimitOffsetPagination
from app.core.responses import error_response, success_response
from .models import Comment, Like, Post, PostStatus
from .serializers import (
    CommentResponseSerializer,
    LikeToggleResponseSerializer,
    MessageSerializer,
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


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 생성에 사용하는 간단한 직렬화기."""

    class Meta:
        model = Comment
        fields = ["id", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class PostLikeToggleAPIView(views.APIView):
    """게시글 좋아요를 토글하는 API (로그인 필요)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Posts"],
        summary="게시글 좋아요 토글",
        responses=LikeToggleResponseSerializer,
        examples=[
            OpenApiExample(
                "Like response",
                value={
                    "message": "좋아요 상태를 변경했습니다.",
                    "data": {"liked": True, "like_count": 12},
                },
                response_only=True,
            )
        ],
    )
    def post(self, request, slug: str):
        qs = Post.objects.all()
        if not request.user.is_staff:
            qs = qs.filter(status=PostStatus.PUBLISHED)
        post = get_object_or_404(qs, slug=slug)
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        return success_response(
            "좋아요 상태를 변경했습니다.",
            {
                "liked": liked,
                "like_count": post.likes.count(),
            },
        )


class CommentCreateAPIView(views.APIView):
    """게시글에 댓글을 추가하는 API."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Posts"],
        summary="게시글 댓글 작성",
        request=CommentCreateSerializer,
        responses=CommentResponseSerializer,
        examples=[
            OpenApiExample(
                "Comment response",
                value={
                    "message": "댓글을 등록했습니다.",
                    "data": {
                        "id": "uuid",
                        "content": "좋은 빌드네요",
                        "created_at": "2025-01-01T12:00:00Z",
                    },
                },
                response_only=True,
            )
        ],
    )
    def post(self, request, slug: str):
        post_qs = Post.objects.all()
        if not request.user.is_staff:
            post_qs = post_qs.filter(status=PostStatus.PUBLISHED)
        post = get_object_or_404(post_qs, slug=slug)
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(
            post=post,
            user=request.user,
            content=serializer.validated_data["content"],
        )
        return success_response(
            "댓글을 등록했습니다.",
            CommentCreateSerializer(comment).data,
            status_code=status.HTTP_201_CREATED,
        )


class CommentDetailAPIView(views.APIView):
    """본인 댓글 수정/삭제 API."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_object(self, request, slug: str, comment_id: str) -> Comment:
        post_qs = Post.objects.all()
        if not request.user.is_staff:
            post_qs = post_qs.filter(status=PostStatus.PUBLISHED)
        post = get_object_or_404(post_qs, slug=slug)
        comment = get_object_or_404(Comment, pk=comment_id, post=post)
        return comment

    def _check_owner(self, request, comment: Comment):
        if comment.user_id != request.user.id:
            return error_response(
                "본인 댓글만 수정/삭제할 수 있습니다.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="FORBIDDEN",
            )
        return None

    @extend_schema(
        tags=["Posts"],
        summary="댓글 수정",
        request=CommentCreateSerializer,
        responses=CommentResponseSerializer,
        examples=[
            OpenApiExample(
                "Comment update response",
                value={
                    "message": "댓글을 수정했습니다.",
                    "data": {
                        "id": "uuid",
                        "content": "수정된 댓글",
                        "created_at": "2025-01-01T12:00:00Z",
                    },
                },
                response_only=True,
            )
        ],
    )
    def patch(self, request, slug: str, comment_id: str):
        comment = self._get_object(request, slug, comment_id)
        maybe_error = self._check_owner(request, comment)
        if maybe_error:
            return maybe_error
        serializer = CommentCreateSerializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("댓글을 수정했습니다.", serializer.data)

    @extend_schema(
        tags=["Posts"],
        summary="댓글 삭제",
        responses=MessageSerializer,
        examples=[
            OpenApiExample(
                "Comment delete response",
                value={
                    "message": "댓글을 삭제했습니다.",
                },
                response_only=True,
            )
        ],
    )
    def delete(self, request, slug: str, comment_id: str):
        comment = self._get_object(request, slug, comment_id)
        maybe_error = self._check_owner(request, comment)
        if maybe_error:
            return maybe_error
        comment.delete()
        return success_response("댓글을 삭제했습니다.")
