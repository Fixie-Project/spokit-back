"""게시글 기능에 쓰이는 폼 모음입니다."""
from __future__ import annotations

import math
from django import forms

from .models import Comment, Post, PostStatus, Submission


class CommentForm(forms.ModelForm):
    """댓글 내용을 입력하는 폼입니다."""

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
    """소개 신청서를 작성하는 폼입니다."""

    sns_links_raw = forms.CharField(
        label="SNS 링크",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Instagram, Blog, YouTube 등 SNS 링크를 줄바꿈으로 입력",
            }
        ),
        help_text="각 줄마다 하나의 링크를 입력하세요.",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["sns_links_raw"].initial = "\n".join(self.instance.sns_links or [])

    def clean_sns_links_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("sns_links_raw"))

    def save(self, commit: bool = True) -> Submission:
        instance: Submission = super().save(commit=False)
        instance.sns_links = self.cleaned_data.get("sns_links_raw", [])
        if commit:
            instance.save()
        return instance


class PostForm(forms.ModelForm):
    """운영자가 게시글을 작성하거나 수정할 때 쓰는 폼입니다."""

    class Meta:
        model = Post
        fields = [
            "title",
            "slug",
            "summary",
            "body",
            "cover_image",
            "status",
            "featured",
            "tags",
        ]
        labels = {
            "title": "제목",
            "slug": "슬러그",
            "summary": "요약",
            "body": "본문",
            "cover_image": "대표 이미지 URL",
            "status": "공개 상태",
            "featured": "추천 노출",
            "tags": "태그",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 10}),
            "tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = PostStatus.choices


class GearCalculatorForm(forms.Form):
    """기어비를 계산하는 간단한 폼입니다."""

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
