"""소개 신청과 부품 정보를 관리하는 모델입니다."""
from __future__ import annotations

import html

from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe

from app.bike.models import Bike, BikeSpec


class SubmissionStatus(models.TextChoices):
    """소개 신청서가 거치는 단계를 정의합니다."""

    SUBMITTED = "submitted", "접수됨"
    IN_REVIEW = "in_review", "대기중"
    IN_PROGRESS = "in_progress", "포스팅중"
    PUBLISHED = "published", "포스팅 완료"
    REJECTED = "rejected", "반려"


class Submission(models.Model):
    """회원이 운영자에게 보내는 소개 신청서입니다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )  # 신청서를 제출한 회원
    title = models.CharField(max_length=200, default="")  # 신청서 제목
    sns_links = models.JSONField(default=list, blank=True)  # 신청자가 공유한 SNS 링크 목록
    message = models.TextField()  # 소개 글 본문(리치 텍스트)
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED,
    )  # 신청 진행 상태
    notes = models.TextField(blank=True)  # 운영자 메모
    rejection_reason = models.TextField(blank=True)  # 반려 사유 기록
    draft_data = models.JSONField(default=dict, blank=True)  # 임시저장된 초안 데이터
    reviewed_at = models.DateTimeField(null=True, blank=True)  # 검토 완료 시각
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
    )  # 검토를 담당한 운영자
    result_post = models.ForeignKey(
        "post.Post",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_submissions",
    )  # 신청서와 연결된 게시글
    bike = models.ForeignKey(
        Bike,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )  # 신청자에게 연결된 자전거 정보
    created_at = models.DateTimeField(auto_now_add=True)  # 신청서 접수 시각

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="submission_status_idx"),
        ]
        db_table = "post_submission"

    def __str__(self) -> str:
        display = self.title or (self.user.get_username() if self.user_id else str(self.pk))
        return f"Submission({display}, {self.status})"

    def ensure_bike(
        self,
        *,
        owner,
        name: str | None = None,
    ) -> Bike:
        """신청서에 연결된 자전거가 없으면 생성하거나 갱신합니다."""

        bike = self.bike
        target_name = name or self.title or f"Submission {self.pk}"
        if bike is None:
            unique_name = target_name
            counter = 1
            if owner:
                exists = Bike.objects.filter(owner=owner, name=unique_name).exists()
                while exists:
                    counter += 1
                    unique_name = f"{target_name} #{counter}"
                    exists = Bike.objects.filter(owner=owner, name=unique_name).exists()
            else:
                exists = Bike.objects.filter(owner__isnull=True, name=unique_name).exists()
                while exists:
                    counter += 1
                    unique_name = f"{target_name} #{counter}"
                    exists = Bike.objects.filter(owner__isnull=True, name=unique_name).exists()
            bike = Bike(
                owner=owner,
                name=unique_name,
            )
        else:
            bike.name = target_name
            if owner and bike.owner_id != owner.pk:
                bike.owner = owner
        bike.save()
        self.bike = bike
        self.save(update_fields=["bike"])
        return bike

    def update_bike_spec(self, data: dict[str, str]) -> BikeSpec:
        """자전거의 부품 정보를 주어진 데이터로 갱신합니다."""

        if not self.bike:
            raise ValueError("bike must be assigned before updating spec")
        spec, _ = BikeSpec.objects.get_or_create(bike=self.bike)
        allowed_fields = {
            field.name
            for field in BikeSpec._meta.get_fields()
            if getattr(field, "concrete", False) and field.name not in {"id", "bike", "updated_at"}
        }
        for field, value in data.items():
            if field in allowed_fields:
                setattr(spec, field, value or "")
        spec.save()
        return spec

    @property
    def message_html(self) -> str:
        """리치 텍스트 메시지를 HTML로 안전하게 반환합니다."""

        if not self.message:
            return ""
        return mark_safe(html.unescape(self.message))


class SubmissionImage(models.Model):
    """신청서에 첨부된 이미지를 저장합니다."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="submission_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        db_table = "post_submission_image"

    def __str__(self) -> str:
        return f"SubmissionImage(submission={self.submission_id}, image={self.image.name})"
