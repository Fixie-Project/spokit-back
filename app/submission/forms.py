"""소개 신청서 작성에 사용되는 폼입니다."""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ClearableFileInput

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Submission, SubmissionImage


class MultiFileInput(ClearableFileInput):
    """다중 파일 업로드를 지원하는 위젯입니다."""

    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """여러 장의 이미지를 업로드할 수 있는 필드입니다."""

    widget = MultiFileInput

    def clean(self, data, initial=None):  # type: ignore[override]
        if not data:
            if self.required and not initial:
                raise ValidationError(self.error_messages["required"], code="required")
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        errors: list[ValidationError] = []
        for file_obj in data:
            try:
                cleaned_files.append(super().clean(file_obj, initial))
            except ValidationError as exc:
                errors.extend(exc.error_list)
        if errors:
            raise ValidationError(errors)
        return cleaned_files


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
    images = MultipleImageField(
        label="이미지",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*"}),
        help_text="픽시 빌드 사진을 여러 장 업로드할 수 있습니다.",
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
            "title",
            "message",
        ]
        labels = {
            "title": "신청서 제목",
            "message": "바이크 설명",
        }
        widgets = {
            "message": CKEditorUploadingWidget(config_name="default"),
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
            self.fields["title"].initial = self.instance.title
            if self.instance.bike:
                spec = getattr(self.instance.bike, "spec", None)
                if spec:
                    for field in self.BUILD_FIELDS:
                        self.fields[field].initial = getattr(spec, field)
        else:
            if self.instance.title:
                self.fields["title"].initial = self.instance.title

    def clean_sns_links_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("sns_links_raw"))

    def save(self, commit: bool = True) -> Submission:
        submission: Submission = super().save(commit=False)
        submission.sns_links = self.cleaned_data.get("sns_links_raw", [])
        submission.save()
        owner = submission.user if submission.user_id else None
        bike = submission.ensure_bike(
            owner=owner,
            name=submission.title,
        )
        spec_data = {
            field: self.cleaned_data.get(field, "")
            for field in self.BUILD_FIELDS
        }
        submission.update_bike_spec(spec_data)
        uploaded_images = self.cleaned_data.get("images", [])
        for image_file in uploaded_images:
            SubmissionImage.objects.create(submission=submission, image=image_file)
        return submission


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]
