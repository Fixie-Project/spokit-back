"""Spokit 전역에서 재사용하는 베이스 모델 정의."""
from __future__ import annotations

import uuid
from typing import Any

from django.db import models


class UUIDPrimaryKeyModel(models.Model):
    """UUID 기본 키를 제공하는 믹스인."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """생성·수정 일시 필드를 추가하는 믹스인."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """소프트 삭제 플래그를 제공하는 믹스인."""

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseModel(UUIDPrimaryKeyModel, TimeStampedModel, SoftDeleteModel):
    """주요 도메인 모델이 상속하는 공통 베이스 모델."""

    class Meta:
        abstract = True


class BaseImage(BaseModel):
    """서비스 전반에서 사용하는 업로드 이미지 메타데이터 모델."""

    url = models.URLField()
    s3_key = models.CharField(max_length=255)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    filesize = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "core_base_image"
        verbose_name = "Image"
        verbose_name_plural = "Images"
        indexes = [
            models.Index(fields=["s3_key"], name="core_base_image_s3_key_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr helper
        return f"Image<{self.s3_key}>"

    def as_dict(self) -> dict[str, Any]:
        """이미지 메타데이터를 직렬화 가능한 형태로 반환."""

        return {
            "url": self.url,
            "s3_key": self.s3_key,
            "width": self.width,
            "height": self.height,
            "filesize": self.filesize,
        }
