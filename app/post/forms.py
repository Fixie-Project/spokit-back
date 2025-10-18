"""게시글 기능에 쓰이는 폼 모음입니다."""
from __future__ import annotations

import math
from django import forms

from .models import Comment, Post, PostStatus


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


class PostForm(forms.ModelForm):
    """운영자가 게시글을 작성하거나 수정할 때 쓰는 폼입니다."""

    class Meta:
        model = Post
        fields = [
            "main_title",
            "sub_title",
            "slug",
            "status",
            "frame_brand",
            "frame_type",
            "content_md",
            "content_html",
            "content_json",
            "tags",
        ]
        labels = {
            "main_title": "메인 타이틀",
            "sub_title": "서브 타이틀",
            "slug": "슬러그",
            "status": "공개 상태",
            "frame_brand": "프레임 브랜드",
            "frame_type": "프레임 타입",
            "content_md": "본문 (Markdown)",
            "content_html": "본문 (HTML)",
            "content_json": "본문 (JSON)",
            "tags": "태그",
        }
        widgets = {
            "content_md": forms.Textarea(attrs={"rows": 10}),
            "content_html": forms.Textarea(attrs={"rows": 10}),
            "tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = PostStatus.choices
        json_field = forms.JSONField(required=True)
        if self.instance and self.instance.pk:
            json_field.initial = self.instance.content_json
        self.fields["content_json"] = json_field


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
