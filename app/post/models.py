"""게시글 앱에서 사용하는 모델 정의입니다."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.urls import reverse


class PostStatus(models.TextChoices):
    """게시글의 진행 상태를 정의합니다."""

    DRAFT = "draft", "초안"
    REVIEW = "review", "검수중"
    PUBLISHED = "published", "게시됨"


class Tag(models.Model):
    """브랜드·지역 등 주제를 나타내는 태그입니다."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"], name="tag_slug_idx")]

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    """운영자가 작성·관리하는 게시글입니다."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField(blank=True)
    body = models.TextField(help_text="마크다운 또는 HTML로 자유롭게 작성")
    cover_image = models.URLField(blank=True)
    spec = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT,
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["slug"], name="post_slug_idx"),
            models.Index(fields=["status", "published_at"], name="post_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("post:detail", args=[self.slug])

    @property
    def is_published(self) -> bool:
        return self.status == PostStatus.PUBLISHED

    def spec_items(self) -> list[tuple[str, Any]]:
        """스펙 정보를 화면에 보여줄 순서대로 정렬합니다."""

        if not isinstance(self.spec, dict):
            return []
        preferred_order = [
            "frame",
            "fork",
            "wheelset",
            "tire",
            "crank",
            "chainring",
            "cog",
            "sprocket",
            "handlebar",
            "stem",
            "saddle",
            "seatpost",
            "pedal",
            "others",
        ]
        items: list[tuple[str, Any]] = []
        seen = set()
        for key in preferred_order:
            value = self.spec.get(key)
            if value:
                items.append((key, value))
                seen.add(key)
        for key, value in self.spec.items():
            if key not in seen and value:
                items.append((key, value))
                seen.add(key)
        return items

    def save(self, *args, **kwargs):
        if self.status == PostStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    """게시글에 달린 댓글을 저장합니다."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.user}: {self.content[:30]}"


class Like(models.Model):
    """회원이 누른 좋아요 정보를 저장합니다."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self) -> str:
        return f"{self.user} → {self.post}"


class SubmissionStatus(models.TextChoices):
    """소개 신청서가 거치는 단계를 나타냅니다."""

    SUBMITTED = "submitted", "접수됨"
    IN_REVIEW = "in_review", "대기중"
    IN_PROGRESS = "in_progress", "포스팅중"
    PUBLISHED = "published", "포스팅 완료"
    REJECTED = "rejected", "반려"


class Submission(models.Model):
    """게시글 소개를 요청한 신청서를 저장합니다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    submitter_name = models.CharField(max_length=100)
    submitter_email = models.EmailField()
    sns_links = models.JSONField(default=list, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED,
    )
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    draft_data = models.JSONField(default=dict, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
    )
    result_post = models.ForeignKey(
        "Post",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_submissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="submission_status_idx"),
            models.Index(fields=["submitter_email"], name="submission_email_idx"),
        ]

    def __str__(self) -> str:
        return f"Submission({self.submitter_name}, {self.status})"
