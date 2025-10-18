"""v2 스키마에 맞춘 신청서 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from app.bike.serializers import BikeSerializer, BikeBuildSerializer

from .models import Submission, SubmissionImage


class SubmissionImageSerializer(serializers.ModelSerializer):
    """신청서 이미지와 기본 메타데이터를 직렬화."""

    class Meta:
        model = SubmissionImage
        fields = [
            "id",
            "url",
            "purpose",
            "order",
            "caption",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class StoryBlockSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    question_text = serializers.CharField(required=False, allow_blank=True)
    answer = serializers.CharField()
    images = serializers.ListField(child=serializers.URLField(), required=False)


class SubmissionSerializer(serializers.ModelSerializer):
    """새 구조에 맞춘 신청서 직렬화기."""

    bike = BikeSerializer(read_only=True)
    build = BikeBuildSerializer(read_only=True)
    story_blocks = serializers.ListField(child=StoryBlockSerializer(), allow_empty=False)
    build_snapshot = serializers.DictField(allow_empty=True)
    images = SubmissionImageSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "user",
            "bike",
            "build",
            "title",
            "build_snapshot",
            "story_blocks",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
            "images",
        ]
        read_only_fields = (
            "id",
            "user",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
            "images",
        )

    def validate_story_blocks(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("스토리 블록은 최소 1개 이상이어야 합니다.")
        for idx, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"{idx}번째 스토리 블록이 올바른 형식이 아닙니다.")
            if not item.get("question_id"):
                raise serializers.ValidationError(f"{idx}번째 블록에 question_id가 필요합니다.")
            if not item.get("answer"):
                raise serializers.ValidationError(f"{idx}번째 블록에 answer가 필요합니다.")
        return value

    def validate_build_snapshot(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("빌드 스냅샷은 딕셔너리 형식이어야 합니다.")
        return value

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        return Submission.objects.create(user=user, **validated_data)

    def update(self, instance: Submission, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
