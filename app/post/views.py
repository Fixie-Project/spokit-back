"""게시글 관련 API 뷰 모음입니다."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from .models import Comment, Like, Post, PostStatus


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 생성에 사용하는 간단한 직렬화기."""
    class Meta:
        model = Comment
        fields = ["id", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class PostLikeToggleAPIView(views.APIView):
    """게시글 좋아요를 토글하는 API (로그인 필요)."""
    permission_classes = [permissions.IsAuthenticated]

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
        return Response({"liked": liked, "like_count": post.likes.count()})


class CommentCreateAPIView(views.APIView):
    """게시글에 댓글을 추가하는 API."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug: str) -> Response:
        post = get_object_or_404(Post, slug=slug)
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(
            post=post,
            user=request.user,
            content=serializer.validated_data["content"],
        )
        return Response(CommentCreateSerializer(comment).data, status=status.HTTP_201_CREATED)


# class GearCalculatorAPIView(views.APIView):
#     """입력받은 톱니수/휠 사이즈로 기어비를 계산합니다."""
#     permission_classes = [permissions.AllowAny]

#     def post(self, request) -> Response:
#         form = GearCalculatorForm(request.data)
#         if not form.is_valid():
#             return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
#         return Response(form.calculate())

