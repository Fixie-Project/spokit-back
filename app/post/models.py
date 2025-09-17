"""Database models for the post application."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.urls import reverse


class PostStatus(models.TextChoices):
    """Workflow status for curated posts."""

    DRAFT = "draft", "초안"
    REVIEW = "review", "검수중"
    PUBLISHED = "published", "게시됨"


class Tag(models.Model):
    """Topic taxonomy such as 브랜드, 지역, 크루 등."""

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
    """Individual blog post curated by the operator."""

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
        """Return spec items in a stable order for rendering."""

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
    """User comments per post."""

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
    """Post likes by authenticated users."""

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
    """Workflow status for community submissions."""

    PENDING = "pending", "대기"
    APPROVED = "approved", "승인"
    REJECTED = "rejected", "반려"


class Submission(models.Model):
    """User-submitted request for post curation."""

    submitter_name = models.CharField(max_length=100)
    submitter_email = models.EmailField()
    links = models.JSONField(default=list, blank=True)
    photos = models.JSONField(default=list, blank=True)
    gear_info = models.JSONField(default=dict, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING,
    )
    notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
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
