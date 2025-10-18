"""Spokit 데이터 스펙에 맞춘 자전거 도메인 모델."""
from __future__ import annotations

from typing import Any, Dict

from django.core.exceptions import ValidationError
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
    frame_brand = models.CharField(max_length=120)
    frame_type = models.CharField(
        max_length=50,
        choices=FrameType.choices,
        blank=True,
    )
    main_image = models.ForeignKey(
        BaseImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="main_bikes",
    )
    is_public = models.BooleanField(default=False)
    is_posted = models.BooleanField(default=False)

    class Meta:
        db_table = "bike_bike"
        verbose_name = "자전거"
        verbose_name_plural = "자전거"
        indexes = [
            models.Index(fields=["frame_brand"], name="bike_frame_brand_idx"),
            models.Index(fields=["frame_type"], name="bike_frame_type_idx"),
            models.Index(fields=["is_public"], name="bike_public_idx"),
            models.Index(fields=["is_posted"], name="bike_posted_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return f"{self.frame_brand} {self.frame_name}" if self.frame_name else str(self.pk)


COMPONENT_SCHEMA: Dict[str, Dict[str, Any]] = {
    "frame_setup": {"details": {"fork", "headset", "spacer"}},
    "wheel": {"details": {"hub", "rim", "spoke", "tire", "cog", "lockring"}},
    "cockpit": {"details": {"handlebar", "stem", "stemcap", "grip", "bartape", "bar_end"}},
    "drivetrain": {"details": {"crank", "bottom_bracket", "chainring", "chain", "pedal", "toe"}},
    "seat": {"details": {"seatpost", "saddle", "seat_clamp"}},
    "brake": {"details": {"brake", "lever"}},
    "etc": {"details": None},
}


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

    class Meta:
        db_table = "bike_build"
        verbose_name = "자전거 빌드"
        verbose_name_plural = "자전거 빌드"
        indexes = [
            models.Index(fields=["base_bike"], name="bike_build_base_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 표시용 헬퍼
        return self.title or f"Build of {self.base_bike_id}"

    def clean(self):
        super().clean()
        self.components = self._normalize_components(self.components)

    def save(self, *args, **kwargs):
        self.components = self._normalize_components(self.components)
        super().save(*args, **kwargs)

    @staticmethod
    def _normalize_components(raw_components: Any) -> dict[str, Any]:
        """정의된 스키마에 맞게 부품 데이터를 정리."""

        if raw_components in (None, ""):
            return {}
        if not isinstance(raw_components, dict):
            raise ValidationError("components 필드는 dict 형태여야 합니다.")

        normalized: dict[str, Any] = {}
        for category, payload in raw_components.items():
            if category not in COMPONENT_SCHEMA:
                continue
            if not isinstance(payload, dict):
                continue

            cleaned_payload: dict[str, Any] = {}
            brand = payload.get("brand")
            model = payload.get("model")
            if brand:
                cleaned_payload["brand"] = brand
            if model:
                cleaned_payload["model"] = model

            details_spec = COMPONENT_SCHEMA[category]["details"]
            raw_details = payload.get("details")
            if isinstance(raw_details, dict) and details_spec is not None:
                cleaned_details = {
                    key: value
                    for key, value in raw_details.items()
                    if key in details_spec and isinstance(value, dict)
                    and any(value.get(field) for field in ("brand", "model"))
                }
                if cleaned_details:
                    cleaned_payload["details"] = cleaned_details
            elif isinstance(raw_details, dict) and details_spec is None:
                cleaned_details = {
                    key: value
                    for key, value in raw_details.items()
                    if isinstance(value, (str, dict)) and value not in ("", None, {})
                }
                if cleaned_details:
                    cleaned_payload["details"] = cleaned_details

            if cleaned_payload:
                normalized[category] = cleaned_payload

        return normalized
