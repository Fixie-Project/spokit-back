"""소개 신청과 부품 정보를 관리하는 모델입니다."""
from __future__ import annotations

from django.conf import settings
from django.db import models


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

    def ensure_build_detail(self) -> "SubmissionBuildDetail":
        """연결된 부품 정보가 없다면 새로 만들어 반환합니다."""

        detail, _ = SubmissionBuildDetail.objects.get_or_create(submission=self)
        return detail

    @property
    def build_detail_safe(self) -> "SubmissionBuildDetail | None":
        """부품 정보가 없으면 None을 돌려줍니다."""

        try:
            return self.build_detail
        except SubmissionBuildDetail.DoesNotExist:
            return None


class SubmissionBuildDetail(models.Model):
    """소개 신청과 함께 제출된 자전거 부품 정보입니다."""

    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name="build_detail",
    )
    frame = models.CharField(max_length=200, blank=True)
    fork = models.CharField(max_length=200, blank=True)
    wheelset = models.CharField(max_length=200, blank=True)
    crank = models.CharField(max_length=200, blank=True)
    chainring = models.CharField(max_length=200, blank=True)
    cog = models.CharField(max_length=200, blank=True)
    handlebar = models.CharField(max_length=200, blank=True)
    stem = models.CharField(max_length=200, blank=True)
    saddle = models.CharField(max_length=200, blank=True)
    seatpost = models.CharField(max_length=200, blank=True)
    pedal = models.CharField(max_length=200, blank=True)
    acc = models.TextField(blank=True, db_column="others")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "소개 신청 부품 정보"
        verbose_name_plural = "소개 신청 부품 정보"
        db_table = "post_submissionbuilddetail"

    def as_dict(self) -> dict[str, str]:
        """비어 있지 않은 항목만 딕셔너리로 돌려줍니다."""

        data = {
            "frame": self.frame,
            "fork": self.fork,
            "wheelset": self.wheelset,
            "crank": self.crank,
            "chainring": self.chainring,
            "cog": self.cog,
            "handlebar": self.handlebar,
            "stem": self.stem,
            "saddle": self.saddle,
            "seatpost": self.seatpost,
            "pedal": self.pedal,
            "acc": self.acc,
        }
        return {key: value for key, value in data.items() if value}

    @property
    def display_items(self) -> list[tuple[str, str]]:
        """템플릿에서 보기 좋게 (한글라벨, 값)을 돌려줍니다."""

        labels = {
            "frame": "프레임",
            "fork": "포크",
            "wheelset": "휠셋",
            "crank": "크랭크",
            "chainring": "체인링",
            "cog": "코그",
            "handlebar": "핸들바",
            "stem": "스템",
            "saddle": "안장",
            "seatpost": "싯포스트",
            "pedal": "페달",
            "acc": "액세서리",
        }
        return [(labels.get(key, key), value) for key, value in self.as_dict().items()]
