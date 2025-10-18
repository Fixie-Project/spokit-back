"""Submission form utilities aligning with the new schema."""
from __future__ import annotations

import json

from django import forms

from .models import Submission


class SubmissionForm(forms.ModelForm):
    """Simple admin form for managing submissions."""

    build_snapshot_raw = forms.CharField(
        label="빌드 스냅샷(JSON)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="JSON 객체 형태로 입력하세요.",
    )
    story_blocks_raw = forms.CharField(
        label="스토리 블록(JSON)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="질문/답변 목록을 JSON 리스트로 입력하세요.",
    )

    class Meta:
        model = Submission
        fields = [
            "user",
            "bike",
            "build",
            "title",
            "status",
            "rejection_reason",
        ]
        widgets = {
            "rejection_reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.build_snapshot:
                self.fields["build_snapshot_raw"].initial = json.dumps(
                    self.instance.build_snapshot, ensure_ascii=False, indent=2
                )
            if self.instance.story_blocks:
                self.fields["story_blocks_raw"].initial = json.dumps(
                    self.instance.story_blocks, ensure_ascii=False, indent=2
                )

    def clean_build_snapshot_raw(self) -> dict:
        raw = (self.cleaned_data.get("build_snapshot_raw") or "").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("유효한 JSON 형식이 아닙니다.") from exc
        if not isinstance(data, dict):
            raise forms.ValidationError("JSON 객체 형태여야 합니다.")
        return data

    def clean_story_blocks_raw(self) -> list:
        raw = (self.cleaned_data.get("story_blocks_raw") or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("유효한 JSON 형식이 아닙니다.") from exc
        if not isinstance(data, list):
            raise forms.ValidationError("JSON 리스트 형태여야 합니다.")
        return data

    def save(self, commit: bool = True) -> Submission:
        submission: Submission = super().save(commit=False)
        submission.build_snapshot = self.cleaned_data.get("build_snapshot_raw", {})
        submission.story_blocks = self.cleaned_data.get("story_blocks_raw", [])
        if commit:
            submission.save()
        return submission
