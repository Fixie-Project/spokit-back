"""Forms for post-related interactions."""
from __future__ import annotations

import math
from typing import Any

from django import forms

from .models import Comment, Submission


class CommentForm(forms.ModelForm):
    """Simple textarea form for comments."""

    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "라이딩 느낌이나 궁금한 점을 남겨주세요.",
                }
            )
        }
        labels = {"content": "댓글"}


class SubmissionForm(forms.ModelForm):
    """Form for build introduction submissions."""

    links_raw = forms.CharField(
        label="참고 링크",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Instagram, Blog, Youtube 링크 등을 줄바꿈으로 입력",
            }
        ),
        help_text="각 줄마다 하나의 링크를 입력하세요.",
    )
    photos_raw = forms.CharField(
        label="사진 링크",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "사진 또는 드라이브 링크를 줄바꿈으로 입력",
            }
        ),
    )
    front_teeth = forms.IntegerField(
        label="앞 톱니 수",
        min_value=1,
        required=False,
    )
    rear_teeth = forms.IntegerField(
        label="뒤 톱니 수",
        min_value=1,
        required=False,
    )
    wheel_size = forms.ChoiceField(
        label="휠 사이즈",
        required=False,
        choices=[
            ("", "선택안함"),
            ("700c", "700C (622mm)"),
            ("650c", "650C (571mm)"),
            ("26", "26인치 (559mm)"),
        ],
    )

    class Meta:
        model = Submission
        fields = [
            "submitter_name",
            "submitter_email",
            "message",
        ]
        labels = {
            "submitter_name": "제출자 이름",
            "submitter_email": "이메일",
            "message": "메시지 / 빌드 소개",
        }
        widgets = {
            "message": forms.Textarea(attrs={"rows": 6}),
        }

    def clean_links_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("links_raw"))

    def clean_photos_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("photos_raw"))

    def save(self, commit: bool = True) -> Submission:
        instance: Submission = super().save(commit=False)
        instance.links = self.cleaned_data.get("links_raw", [])
        instance.photos = self.cleaned_data.get("photos_raw", [])
        gear_info: dict[str, Any] = {}
        front = self.cleaned_data.get("front_teeth")
        rear = self.cleaned_data.get("rear_teeth")
        wheel = self.cleaned_data.get("wheel_size")
        if front:
            gear_info["front_teeth"] = front
        if rear:
            gear_info["rear_teeth"] = rear
        if wheel:
            gear_info["wheel_size"] = wheel
        if gear_info:
            instance.gear_info = gear_info
        if commit:
            instance.save()
        return instance


class GearCalculatorForm(forms.Form):
    """Simple gear ratio calculator form."""

    WHEEL_SIZES = {
        "700c": 622,
        "650c": 571,
        "26": 559,
        "24": 507,
        "20": 451,
    }

    front_teeth = forms.IntegerField(label="앞 체인링 톱니 수", min_value=1)
    rear_teeth = forms.IntegerField(label="뒤 코그 톱니 수", min_value=1)
    wheel_size = forms.ChoiceField(
        label="휠 사이즈",
        choices=[(key, f"{key.upper()} ({value}mm)") for key, value in WHEEL_SIZES.items()],
        initial="700c",
    )

    def calculate(self) -> dict[str, float]:
        front = self.cleaned_data["front_teeth"]
        rear = self.cleaned_data["rear_teeth"]
        wheel_key = self.cleaned_data["wheel_size"]
        ratio = front / rear
        diameter_mm = self.WHEEL_SIZES[wheel_key]
        diameter_inch = diameter_mm / 25.4
        gear_inches = ratio * diameter_inch
        rollout_mm = ratio * diameter_mm * math.pi
        rollout_meter = rollout_mm / 1000
        return {
            "ratio": round(ratio, 2),
            "gear_inches": round(gear_inches, 2),
            "rollout_m": round(rollout_meter, 2),
        }


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]
