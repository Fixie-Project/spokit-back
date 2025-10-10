"""소개 신청서 작성에 사용되는 폼입니다."""
from __future__ import annotations

import json

from django import forms
from .models import Submission
from .questions import DEFAULT_QUESTION_VERSION, load_question_set

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
    story_blocks_raw = forms.CharField(
        label="스토리 블록(JSON)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": '[{"question_id": "q1", "question_text": "...", "answer": "...", "images": []}]',
            }
        ),
        help_text="질문과 답변을 JSON 리스트 형식으로 입력하세요.",
    )
    required_questions = forms.MultipleChoiceField(
        label="답변할 질문 선택",
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        help_text="사이트에서 답변할 질문을 선택하거나 노션 링크에 답변을 정리해 주세요.",
    )
    external_story_url = forms.URLField(
        label="인터뷰 스토리 링크",
        required=False,
        widget=forms.URLInput(
            attrs={
                "placeholder": "Notion 템플릿 또는 외부 문서 링크",
            }
        ),
        help_text="노션 템플릿으로 작성했다면 링크를 추가해 주세요.",
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
            "external_story_url",
        ]
        labels = {
            "title": "신청서 제목",
        }
        widgets: dict = {}

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
        self.question_version = (
            getattr(self.instance, "question_version", None) or DEFAULT_QUESTION_VERSION
        )
        question_set = load_question_set(self.question_version)
        self.question_set = question_set
        choices = question_set.to_group_choices(include_non_selectable=False)
        self.fields["required_questions"].choices = choices
        selectable_ids = {
            question_id
            for _, items in choices
            for question_id, _ in items
        }
        if self.instance and self.instance.pk:
            self.fields["sns_links_raw"].initial = "\n".join(self.instance.sns_links or [])
            self.fields["title"].initial = self.instance.title
            self.fields["external_story_url"].initial = self.instance.external_story_url
            self.fields["required_questions"].initial = [
                qid
                for qid in (self.instance.required_question_ids or [])
                if qid in selectable_ids
            ]
            self.fields["story_blocks_raw"].initial = json.dumps(
                self.instance.story_blocks or [], ensure_ascii=False, indent=2
            )
            if self.instance.bike:
                spec = getattr(self.instance.bike, "spec", None)
                if spec:
                    for field in self.BUILD_FIELDS:
                        self.fields[field].initial = getattr(spec, field)
        else:
            if self.instance.title:
                self.fields["title"].initial = self.instance.title
            self.fields["story_blocks_raw"].initial = ""
            self.fields["required_questions"].initial = [
                qid
                for qid in question_set.required_ids
                if qid in selectable_ids
            ]

    def clean_sns_links_raw(self) -> list[str]:
        return _split_lines(self.cleaned_data.get("sns_links_raw"))

    def clean_story_blocks_raw(self):
        raw = (self.cleaned_data.get("story_blocks_raw") or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("유효한 JSON 형식이 아닙니다.") from exc
        if not isinstance(data, list):
            raise forms.ValidationError("스토리 블록은 리스트 형태여야 합니다.")
        return data

    def clean_external_story_url(self) -> str:
        url = self.cleaned_data.get("external_story_url")
        return (url or "").strip()

    def clean(self):  # type: ignore[override]
        cleaned_data = super().clean()
        external_story_url = (cleaned_data.get("external_story_url") or "").strip()
        story_blocks = cleaned_data.get("story_blocks_raw") or []
        if not external_story_url and not story_blocks:
            raise forms.ValidationError(
                "스토리 블록을 입력하거나 외부 링크를 입력해 주세요."
            )
        cleaned_data["external_story_url"] = external_story_url
        return cleaned_data

    def save(self, commit: bool = True) -> Submission:
        submission: Submission = super().save(commit=False)
        submission.sns_links = self.cleaned_data.get("sns_links_raw", [])
        submission.story_blocks = self.cleaned_data.get("story_blocks_raw", [])
        submission.external_story_url = self.cleaned_data.get("external_story_url", "")
        selected_ids = list(self.cleaned_data.get("required_questions", []))
        selected_set = set(selected_ids)

        # include existing ids that may not be selectable (e.g., final signature question)
        existing_ids = submission.required_question_ids or []
        for qid in existing_ids:
            if qid not in selected_set:
                selected_ids.append(qid)
                selected_set.add(qid)

        # ensure all required ids are present
        for required_id in self.question_set.required_ids:
            if required_id not in selected_set:
                selected_ids.append(required_id)
                selected_set.add(required_id)

        submission.required_question_ids = selected_ids
        submission.question_version = self.question_version
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
        return submission


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]
