"""게시글 관련 직렬화기 모음."""
from __future__ import annotations

from rest_framework import serializers

from app.core.models import BaseImage

from app.submission.models import Submission

from .models import Comment, Post, PostImage, PostImagePurpose, PostStatus, Tag


class TagSerializer(serializers.ModelSerializer):
    """태그 정보를 직렬화."""

    class Meta:
        model = Tag
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    """게시글 댓글 데이터를 직렬화."""

    user = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "created_at"]
        read_only_fields = fields


class PostImageSerializer(serializers.ModelSerializer):
    """게시글과 연결된 이미지 정보를 직렬화."""

    class Meta:
        model = PostImage
        fields = [
            "id",
            "url",
            "purpose",
            "order",
            "caption",
            "created_at",
        ]
        read_only_fields = fields


class PostImageWriteSerializer(serializers.Serializer):
    """게시글 이미지 생성용 입력."""

    base_image = serializers.PrimaryKeyRelatedField(queryset=BaseImage.objects.all())
    purpose = serializers.ChoiceField(choices=PostImagePurpose.choices)
    order = serializers.IntegerField(required=False, default=0)
    caption = serializers.CharField(required=False, allow_blank=True, default="")


class PostSerializer(serializers.ModelSerializer):
    """게시글을 조회할 때 필요한 상세 정보를 제공."""

    author = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)
    thumbnail_image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "submission",
            "rider",
            "main_title",
            "sub_title",
            "content_md",
            "content_html",
            "content_json",
            "frame_brand",
            "frame_type",
            "slug",
            "status",
            "published_at",
            "created_at",
            "updated_at",
            "is_editor_pick",
            "tags",
            "images",
            "thumbnail_image",
            "like_count",
            "comment_count",
            "is_liked",
        ]
        read_only_fields = (
            "id",
            "author",
            "submission",
            "rider",
            "published_at",
            "created_at",
            "updated_at",
            "view_count",
            "is_editor_pick",
            "tags",
            "images",
            "like_count",
            "comment_count",
            "is_liked",
        )

    def get_submission(self, obj: Post):
        submission: Submission | None = getattr(obj, "submission", None)
        if not submission:
            return None
        return {
            "id": str(submission.id),
            "status": submission.status,
            "build_snapshot": getattr(obj, "build_snapshot", None) or submission.build_snapshot,
            "story_snapshot": getattr(obj, "story_snapshot", None) or submission.story_blocks,
            "rider_snapshot": getattr(obj, "rider_snapshot", None) or getattr(submission, "rider_snapshot", {}),
        }

    def get_author(self, obj: Post):
        author = getattr(obj, "author", None)  # author는 Staff
        if not author:
            return None
        user = getattr(author, "user", None)
        if user:
            return {"id": user.id, "nickname": user.nickname or user.username}
        # 혹시나 Staff에 user가 없을 때도 안전하게 처리
        return None

    def get_comment_count(self, obj: Post) -> int:
        count = getattr(obj, "comment_count", None)
        if count is not None:
            return count
        return obj.comments.count()

    def get_is_liked(self, obj: Post) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        prefetched_likes = obj._prefetched_objects_cache.get("likes") if hasattr(obj, "_prefetched_objects_cache") else None
        if prefetched_likes is not None:
            return any(like.user_id == user.id for like in prefetched_likes)
        return obj.likes.filter(user=user).exists()

    def get_thumbnail_image(self, obj: Post):
        images = getattr(obj, "_prefetched_objects_cache", {}).get("images") if hasattr(obj, "_prefetched_objects_cache") else None
        if images is None:
            images = list(obj.images.all())
        thumb = next((i for i in images if i.purpose == PostImagePurpose.THUMBNAIL), None)
        if thumb:
            return {"url": thumb.url, "purpose": thumb.purpose, "order": thumb.order, "caption": thumb.caption}
        # fallback: header/hero/body 중 가장 낮은 order
        priority = {PostImagePurpose.HEADER: 0, PostImagePurpose.HERO: 1, PostImagePurpose.BODY: 2}
        sorted_imgs = sorted(images, key=lambda i: (priority.get(i.purpose, 99), i.order))
        if sorted_imgs:
            img = sorted_imgs[0]
            return {"url": img.url, "purpose": img.purpose, "order": img.order, "caption": img.caption}
        return None


class PostWriteSerializer(serializers.ModelSerializer):
    """게시글 생성·수정 시 사용하는 직렬화기."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )
    images = PostImageWriteSerializer(many=True, required=False, write_only=True, allow_empty=True)

    class Meta:
        model = Post
        fields = [
            "author",
            "submission",
            "bike",
            "build",
            "build_snapshot",
            "rider",
            "main_title",
            "sub_title",
            "content_md",
            "content_html",
            "content_json",
            "frame_brand",
            "frame_type",
            "slug",
            "status",
            "is_editor_pick",
            "tags",
            "images",
        ]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        images = validated_data.pop("images", None)
        post = super().create(validated_data)
        if tags:
            post.tags.set(tags)
        if post.sync_snapshots_from_submission(force=True):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        if images is not None:
            self._set_images(post, images)
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        images = validated_data.pop("images", None)
        post = super().update(instance, validated_data)
        if tags is not None:
            post.tags.set(tags)
        if post.sync_snapshots_from_submission(force=False):
            post.save(update_fields=["build_snapshot", "story_snapshot", "updated_at"])
        if images is not None:
            self._set_images(post, images)
        return post

    def _set_images(self, post: Post, images_data: list[dict]):
        PostImage.objects.filter(post=post).delete()
        objs = []
        for idx, item in enumerate(images_data):
            base_image: BaseImage = item["base_image"]
            purpose = item.get("purpose", PostImagePurpose.BODY)
            order = item.get("order", idx)
            caption = item.get("caption", "")
            objs.append(
                PostImage(
                    post=post,
                    purpose=purpose,
                    order=order,
                    caption=caption,
                    url=base_image.url,
                    s3_key=base_image.s3_key,
                    width=base_image.width,
                    height=base_image.height,
                    filesize=base_image.filesize,
                )
            )
        if objs:
            PostImage.objects.bulk_create(objs)


class PostDetailSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["view_count"]
        read_only_fields = PostSerializer.Meta.read_only_fields + ("view_count",)


class PostListSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = [
            "id",
            "author",
            "slug",
            "main_title",
            "sub_title",
            "thumbnail_image",
            "created_at",
            "is_editor_pick",
            "tags",
            "like_count",
            "comment_count",
            "is_liked",
        ]
        read_only_fields = fields


class MessageSerializer(serializers.Serializer):
    """단순 메시지 래퍼."""

    message = serializers.CharField()


class PostListDataSerializer(serializers.Serializer):
    """게시글 목록 data 영역."""

    count = serializers.IntegerField()
    results = PostListSerializer(many=True)


class PostListResponseSerializer(MessageSerializer):
    """게시글 목록 래퍼."""

    data = PostListDataSerializer()


class PostDetailResponseSerializer(MessageSerializer):
    """게시글 단건 래퍼."""

    data = PostDetailSerializer()


class LikeToggleResponseSerializer(MessageSerializer):
    """좋아요 토글 응답 래퍼."""

    data = serializers.DictField()


class CommentResponseSerializer(MessageSerializer):
    """댓글 생성 응답 래퍼."""

    data = CommentSerializer()
