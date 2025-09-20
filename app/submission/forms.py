"""소개 신청서 작성에 사용되는 폼입니다."""
from __future__ import annotations

from django import forms

from .models import Submission


class SubmissionForm(forms.ModelForm):
    """소개 신청서를 작성하거나 수정할 때 쓰는 폼입니다."""

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
    frame = forms.CharField(label="프레임", max_length=200, required=False)
    fork = forms.CharField(label="포크", max_length=200, required=False)
    wheelset = forms.CharField(label="휠셋", max_length=200, required=False)
    crank = forms.CharField(label="크랭크", max_length=200, required=False)
    chainring = forms.CharField(label="체인링", max_length=200, required=False)
    cog = forms.CharField(label="코그", max_length=200, required=False)
    handlebar = forms.CharField(label="핸들바", max_length=200, required=False)
    stem = forms.CharField(label="스템", max_length=200, required=False)
    saddle = forms.CharField(label="안장", max_length=200, required=False)
    seatpost = forms.CharField(label="싯포스트", max_length=200, required=False)
    pedal = forms.CharField(label="페달", max_length=200, required=False)
    acc = forms.CharField(
        label="액세서리", required=False, widget=forms.Textarea(attrs={"rows": 3})
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

    BUILD_FIELDS = [
        "frame",
        "fork",
        "wheelset",
        "crank",
        "chainring",
        "cog",
        "handlebar",
        "stem",
        "saddle",
        "seatpost",
        "pedal",
        "acc",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["sns_links_raw"].initial = "\n".join(self.instance.sns_links or [])
            detail = self.instance.build_detail_safe
            if detail:
                for field in self.BUILD_FIELDS:
                    self.fields[field].initial = getattr(detail, field)

    def clean_sns_links_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("sns_links_raw"))

    def save(self, commit: bool = True) -> Submission:
        submission: Submission = super().save(commit=False)
        submission.sns_links = self.cleaned_data.get("sns_links_raw", [])
        if commit:
            submission.save()
        detail = submission.ensure_build_detail()
        for field in self.BUILD_FIELDS:
            setattr(detail, field, self.cleaned_data.get(field, ""))
        detail.save()
        return submission


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]
