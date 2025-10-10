"""Studio 앱 모델 정의."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from app.post.models import Post, PostStatus
from app.submission.models import Submission


class SubmissionReviewNote(models.Model):
    """운영자가 신청서를 검토하며 남기는 메모입니다."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="review_notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_review_notes",
    )
    post = models.ForeignKey(
        Post,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_review_notes",
    )
    post_status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        blank=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "신청서 검토 메모"
        verbose_name_plural = "신청서 검토 메모"

    def __str__(self) -> str:  # pragma: no cover - 문자열 표현 단순화
        submission_title = self.submission.title or f"Submission {self.submission_id}"
        return f"{submission_title} - {self.author or '운영자'}"
