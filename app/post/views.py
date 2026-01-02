"""게시글 관련 API 뷰 모음입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiExample, extend_schema

from app.core.responses import success_response
from .models import Comment, Like, Post, PostStatus
from .serializers import CommentResponseSerializer, LikeToggleResponseSerializer


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
    def post(self, request, slug: str) -> Response:
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
    def post(self, request, slug: str) -> Response:
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


# class GearCalculatorAPIView(views.APIView):
#     """입력받은 톱니수/휠 사이즈로 기어비를 계산합니다."""
#     permission_classes = [permissions.AllowAny]

#     def post(self, request) -> Response:
#         form = GearCalculatorForm(request.data)
#         if not form.is_valid():
#             return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
#         return Response(form.calculate())
