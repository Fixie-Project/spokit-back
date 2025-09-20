"""소개 신청과 부품 정보를 관리하는 모델입니다."""
from __future__ import annotations

from django.conf import settings
from django.db import models

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
        "post.Post",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_submissions",
    )
    bike = models.ForeignKey(
        Bike,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="submission_status_idx"),
            models.Index(fields=["submitter_email"], name="submission_email_idx"),
        ]
        db_table = "post_submission"

    def __str__(self) -> str:
        return f"Submission({self.submitter_name}, {self.status})"

    def ensure_bike(self, *, owner, name: str, nickname: str = "", description: str = "") -> Bike:
        """신청서에 연결된 자전거가 없으면 생성하거나 갱신합니다."""

        bike = self.bike
        if bike is None:
            unique_name = name
            counter = 1
            if owner:
                exists = Bike.objects.filter(owner=owner, name=unique_name).exists()
                while exists:
                    counter += 1
                    unique_name = f"{name} #{counter}"
                    exists = Bike.objects.filter(owner=owner, name=unique_name).exists()
            else:
                exists = Bike.objects.filter(owner__isnull=True, name=unique_name).exists()
                while exists:
                    counter += 1
                    unique_name = f"{name} #{counter}"
                    exists = Bike.objects.filter(owner__isnull=True, name=unique_name).exists()
            bike = Bike(owner=owner, name=unique_name, nickname=nickname, description=description)
        else:
            bike.name = name
            bike.nickname = nickname
            bike.description = description
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
