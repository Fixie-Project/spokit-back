"""Spokit 데이터 스펙에 맞춘 자전거 도메인 모델."""
from __future__ import annotations

from django.db import models

from app.core.models import BaseImage, BaseModel


class FrameType(models.TextChoices):
    """자전거 프레임 소재 선택지."""

    ALLOY = "Alloy", "알루미늄"
    CARBON = "Carbon", "카본"
    CHROMOLY = "Chromoly", "크로몰리"
    STEEL = "Steel", "강철"
    TITANIUM = "Titanium", "티타늄"


class Bike(BaseModel):
    """사용자가 등록한 자전거 프레임 정보."""

    owner = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bikes",
    )
    name = models.CharField(max_length=120, blank=True)
    frame_name = models.CharField(max_length=120)
    main_image = models.ForeignKey(
        BaseImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="main_bikes",
    )
    is_posted = models.BooleanField(default=False)

    class Meta:
        db_table = "bike_bike"
        verbose_name = "자전거"
        verbose_name_plural = "자전거"
        indexes = [
            models.Index(fields=["is_posted"], name="bike_posted_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.frame_name or str(self.pk)


class BikeBuild(BaseModel):
    """프레임별 빌드 구성을 나타내는 모델."""

    base_bike = models.ForeignKey(
        Bike,
        on_delete=models.CASCADE,
        related_name="builds",
    )
    title = models.CharField(max_length=120, blank=True)
    components = models.JSONField(default=dict)
    note = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    main_image = models.ForeignKey(
        BaseImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="build_main_images",
    )

    class Meta:
        db_table = "bike_build"
        verbose_name = "자전거 빌드"
        verbose_name_plural = "자전거 빌드"
        indexes = [
            models.Index(fields=["base_bike"], name="bike_build_base_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.title or f"Build of {self.base_bike_id}"


class BikeBuildLike(BaseModel):
    """사용자별 빌드 좋아요 기록."""

    build = models.ForeignKey(
        BikeBuild,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="build_likes",
    )

    class Meta:
        db_table = "bike_build_like"
        verbose_name = "빌드 좋아요"
        verbose_name_plural = "빌드 좋아요"
        unique_together = ("build", "user")


class BuildImage(BaseModel):
    """빌드에 연결되는 추가 이미지."""

    build = models.ForeignKey(
        BikeBuild,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ForeignKey(
        BaseImage,
        on_delete=models.CASCADE,
        related_name="build_images",
    )
    order = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "bike_build_image"
        verbose_name = "빌드 이미지"
        verbose_name_plural = "빌드 이미지"
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["build", "order"], name="bike_build_image_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.build_id} · {self.order}"
