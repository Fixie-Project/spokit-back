"""회원이 등록한 자전거와 부품 정보를 정의합니다."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class Bike(models.Model):
    """회원이 보유한 자전거 기본 정보입니다."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bikes",
    )
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner", "-is_primary", "name"]
        unique_together = ("owner", "name")

    def __str__(self) -> str:
        display = self.nickname or self.name
        return f"{display} ({self.owner})"


class BikeSpec(models.Model):
    """자전거를 구성하는 핵심 부품 목록입니다."""

    bike = models.OneToOneField(
        Bike,
        on_delete=models.CASCADE,
        related_name="spec",
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
    acc = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "바이크 부품"
        verbose_name_plural = "바이크 부품"

    def as_dict(self) -> dict[str, str]:
        """비어 있지 않은 부품만 딕셔너리로 반환합니다."""

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
        """템플릿에서 사용하기 좋은 (라벨, 값) 목록입니다."""

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
