"""Spokit 스펙에 맞춘 게시글 및 태그 모델."""
from __future__ import annotations

from typing import Any

from django.db import models
from django.urls import reverse
from django.utils import timezone

from app.bike.models import FrameType
from app.core.models import BaseImage, BaseModel


class PostStatus(models.TextChoices):
    """게시글 진행 상태 코드."""

    DRAFT = "draft", "초안"
    REVIEW = "review", "검토중"
    PUBLISHED = "published", "발행"


class Tag(BaseModel):
    """검색·분류에 사용하는 태그 모델."""

    is_active = None  # 태그는 소프트 삭제 플래그가 필요하지 않음

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "post_tag"
        ordering = ["name"]
        verbose_name = "태그"
        verbose_name_plural = "태그"
        indexes = [
            models.Index(fields=["name"], name="post_tag_name_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.name


class Post(BaseModel):
    """신청서 기반 혹은 운영진 작성 게시글 정보."""

    author = models.ForeignKey(
        "user.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    submission = models.OneToOneField(
        "submission.Submission",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="post",
    )
    bike = models.ForeignKey(
        "bike.Bike",
        on_delete=models.PROTECT,
        related_name="posts",
    )
    build = models.ForeignKey(
        "bike.BikeBuild",
        on_delete=models.PROTECT,
        related_name="posts",
    )
    build_snapshot = models.JSONField(default=dict)
    story_snapshot = models.JSONField(default=list)
    rider_snapshot = models.JSONField(default=dict)
    rider = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="featured_posts",
    )
    main_title = models.CharField(max_length=200)
    sub_title = models.CharField(max_length=200)
    content_md = models.TextField(blank=True)
    content_html = models.TextField()
    content_json = models.JSONField()
    frame_brand = models.CharField(max_length=120)
    frame_type = models.CharField(
        max_length=50,
        blank=True,
        choices=FrameType.choices,
    )
    slug = models.SlugField(unique=True)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    is_editor_pick = models.BooleanField(default=False)

    class Meta:
        db_table = "post_post"
        verbose_name = "게시글"
        verbose_name_plural = "게시글"
        indexes = [
            models.Index(fields=["slug"], name="post_slug_idx"),
            models.Index(fields=["frame_brand"], name="post_frame_brand_idx"),
            models.Index(fields=["frame_type"], name="post_frame_type_idx"),
            models.Index(fields=["status"], name="post_status_idx"),
            models.Index(fields=["published_at"], name="post_published_at_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.main_title

    def get_absolute_url(self) -> str:
        return reverse("post:detail", args=[self.slug])

    def save(self, *args, **kwargs):
        if self.status == PostStatus.PUBLISHED:
            if self.published_at is None:
                self.published_at = timezone.now()
        else:
            self.published_at = None
        super().save(*args, **kwargs)

    def as_dict(self) -> dict[str, Any]:
        """간단한 응답 생성을 위한 요약 딕셔너리."""

        return {
            "id": str(self.pk),
            "main_title": self.main_title,
            "sub_title": self.sub_title,
            "frame_brand": self.frame_brand,
            "frame_type": self.frame_type,
            "status": self.status,
            "slug": self.slug,
        }

    def sync_snapshots_from_submission(self, *, force: bool = False) -> bool:
        """Copy immutable data from submission to local snapshots."""

        if not self.submission_id:
            return False

        changed = False
        submission = self.submission

        if force or not self.build_snapshot:
            snapshot = submission.build_snapshot or {}
            if snapshot != self.build_snapshot:
                self.build_snapshot = snapshot
                changed = True

        if force or not self.story_snapshot:
            story_data = submission.story_blocks or []
            if story_data != self.story_snapshot:
                self.story_snapshot = story_data
                changed = True

        if force or not self.rider_snapshot:
            rider = getattr(submission, "user", None)
            rider_snap = _build_rider_snapshot(rider) if rider else {}
            if rider_snap != self.rider_snapshot:
                self.rider_snapshot = rider_snap
                changed = True

        return changed


class PostImagePurpose(models.TextChoices):
    """게시글 이미지 용도 구분 코드."""

    THUMBNAIL = "thumbnail", "썸네일"
    HEADER = "header", "헤더"
    HERO = "hero", "히어로"
    BODY = "body", "본문"


class PostImage(BaseImage):
    """게시글과 매핑된 이미지 메타데이터."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images",
    )
    purpose = models.CharField(max_length=20, choices=PostImagePurpose.choices)
    order = models.PositiveSmallIntegerField(default=0)
    caption = models.CharField(max_length=255, blank=True)
    source_image = models.ForeignKey(
        "submission.SubmissionImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derived_images",
    )

    class Meta:
        db_table = "post_post_image"
        verbose_name = "게시글 이미지"
        verbose_name_plural = "게시글 이미지"
        ordering = ["purpose", "order", "created_at"]
        indexes = [
            models.Index(fields=["post", "purpose"], name="post_image_post_purpose_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.get_purpose_display()} · {self.post_id}"


class Comment(BaseModel):
    """게시글에 남겨진 사용자 댓글."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField()

    class Meta:
        db_table = "post_comment"
        verbose_name = "댓글"
        verbose_name_plural = "댓글"
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.user}: {self.content[:20]}"


class Like(BaseModel):
    """사용자별 게시글 좋아요 기록."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="likes",
    )

    class Meta:
        db_table = "post_like"
        verbose_name = "좋아요"
        verbose_name_plural = "좋아요"
        unique_together = ("post", "user")


def _build_rider_snapshot(user) -> dict[str, Any]:
    if not user:
        return {}
    image = getattr(user, "profile_image", None)
    image_payload = (
        {"url": image.url, "width": image.width, "height": image.height} if image else None
    )
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "username": user.username,
        "intro": user.intro,
        "region": user.region,
        "sns_link": user.sns_link,
        "profile_image": image_payload,
    }

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.user} → {self.post}"
