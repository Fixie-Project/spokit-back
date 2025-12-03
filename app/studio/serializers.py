"""Studio-only serializers for staff-facing views."""
from __future__ import annotations

from rest_framework import serializers

from app.submission.models import Submission, SubmissionStatus
from app.submission.serializers import SubmissionSerializer
from app.user.models import User


class RiderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "nickname", "region", "intro", "sns_link"]
        read_only_fields = fields


class StudioSubmissionSerializer(SubmissionSerializer):
    """확장된 신청서 직렬화기(운영진 뷰용)."""

    rider = RiderSummarySerializer(source="user", read_only=True)

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + ["rider"]
        read_only_fields = SubmissionSerializer.Meta.read_only_fields


class SubmissionStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SubmissionStatus.choices)
    reason_code = serializers.CharField(required=False, allow_blank=True)
    reason_detail = serializers.CharField(required=False, allow_blank=True)

