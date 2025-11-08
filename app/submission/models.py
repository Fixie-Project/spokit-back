"""Spokit 데이터 기준에 맞춘 신청 관련 모델."""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from app.bike.models import Bike, BikeBuild
from app.core.models import BaseImage, BaseModel


class SubmissionStatus(models.TextChoices):
    """신청서 진행 상태 코드."""

    DRAFT = "draft", "초안"
    SUBMITTED = "submitted", "접수"
    IN_REVIEW = "in_review", "검토중"
    APPROVED = "approved", "승인"
    POSTING = "posting", "포스팅중"
    PUBLISHED = "published", "게시 완료"
    REJECTED = "rejected", "반려"
    RESUBMITTED = "resubmitted", "재신청"


class SubmissionRejectionReason(models.TextChoices):
    """신청서 반려 사유 코드."""

    CONTENT_INCOMPLETE = "content_incomplete", "콘텐츠 보완 필요"
    PHOTO_ISSUE = "photo_issue", "이미지 품질 문제"
    GUIDELINE_MISMATCH = "guideline_mismatch", "가이드라인 불일치"
    DUPLICATE = "duplicate", "중복 신청"
    OTHER = "other", "기타"


class Submission(BaseModel):
    """사용자가 작성한 소개 신청서."""

    user = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    bike = models.ForeignKey(
        Bike,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    build = models.ForeignKey(
        BikeBuild,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    title = models.CharField(max_length=200)
    build_snapshot = models.JSONField(default=dict)
    story_blocks = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT)
    reason_code = models.CharField(
        max_length=40,
        choices=SubmissionRejectionReason.choices,
        blank=True,
    )
    reason_detail = models.TextField(blank=True)

    class Meta:
        db_table = "submission_submission"
        verbose_name = "신청서"
        verbose_name_plural = "신청서"
        indexes = [
            models.Index(fields=["status"], name="submission_status_idx"),
            models.Index(fields=["user"], name="submission_user_idx"),
            models.Index(fields=["created_at"], name="submission_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.title

    def clean(self):
        super().clean()
        if self.build and self.bike and self.build.base_bike_id != self.bike_id:
            raise ValidationError("빌드는 선택된 자전거와 연결되어 있어야 합니다.")
        if not isinstance(self.story_blocks, list):
            raise ValidationError({"story_blocks": "스토리 블록은 리스트 형태여야 합니다."})
        if not isinstance(self.build_snapshot, dict):
            raise ValidationError({"build_snapshot": "빌드 스냅샷은 dict 형태여야 합니다."})

        if self.status == SubmissionStatus.REJECTED:
            if not self.reason_code:
                raise ValidationError({"reason_code": "반려 사유 코드를 선택해 주세요."})
        else:
            self.reason_code = ""
            self.reason_detail = ""

    def save(self, *args, **kwargs):
        self.full_clean(exclude=None)
        super().save(*args, **kwargs)

    def to_snapshot(self) -> dict[str, Any]:
        """게시글과 연동할 때 사용하는 스냅샷 데이터 반환."""

        return {
            "id": str(self.pk),
            "title": self.title,
            "build_snapshot": self.build_snapshot,
            "story_blocks": self.story_blocks,
            "status": self.status,
        }


class SubmissionImagePurpose(models.TextChoices):
    """신청서 이미지 용도 구분."""

    STORY = "story", "스토리"
    EXTRA = "extra", "추가"


class SubmissionImage(BaseImage):
    """신청서에 첨부된 이미지 메타데이터."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="images",
    )
    purpose = models.CharField(max_length=20, choices=SubmissionImagePurpose.choices)
    order = models.IntegerField(null=True, blank=True)
    caption = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "submission_submission_image"
        verbose_name = "신청서 이미지"
        verbose_name_plural = "신청서 이미지"
        ordering = ["purpose", "order", "created_at"]
        indexes = [
            models.Index(fields=["submission", "purpose"], name="submission_image_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.submission_id} · {self.get_purpose_display()}"


class SubmissionStatusLog(BaseModel):
    """신청서 상태 변경 이력을 기록하는 로그."""

    is_active = None  # 로그 레코드는 수정·삭제하지 않음

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    changed_by_staff = models.ForeignKey(
        "user.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_status_logs",
    )
    changed_by_user = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_status_logs",
    )
    from_status = models.CharField(max_length=50, choices=SubmissionStatus.choices)
    to_status = models.CharField(max_length=50, choices=SubmissionStatus.choices)
    comment = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "submission_status_log"
        verbose_name = "신청서 상태 로그"
        verbose_name_plural = "신청서 상태 로그"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(changed_by_staff__isnull=False, changed_by_user__isnull=True)
                    | models.Q(changed_by_staff__isnull=True, changed_by_user__isnull=False)
                ),
                name="submission_log_single_actor",
            ),
        ]

    def clean(self):
        super().clean()
        if bool(self.changed_by_staff) == bool(self.changed_by_user):
            raise ValidationError("운영진 또는 사용자 중 한 명만 상태를 변경할 수 있습니다.")

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.submission_id}: {self.from_status} → {self.to_status}"
