"""v2 스키마에 맞춘 신청서 직렬화기."""
from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from app.bike.models import Bike, BikeBuild
from app.bike.serializers import (
    BikeSerializer,
    BikeBuildSerializer,
    BikeBuildWriteSerializer,
)

from .models import Submission, SubmissionImage, SubmissionRejectionReason
from .questions import load_question_set
from .services import build_to_snapshot


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


class SubmissionNewBikeSerializer(serializers.Serializer):
    """신규 빌드 생성 시 필요한 자전거 정보."""

    frame_name = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False, default=False)


class SubmissionNewBuildSerializer(BikeBuildWriteSerializer):
    """신규 빌드 생성 시 필요한 빌드 정보 (base_bike 제외)."""

    class Meta(BikeBuildWriteSerializer.Meta):
        model = BikeBuild
        fields = ("title", "components", "note", "is_public")
        read_only_fields: tuple = ()


class SubmissionNewBuildPayloadSerializer(serializers.Serializer):
    """신규 자전거 + 빌드를 함께 생성하기 위한 페이로드."""

    bike = SubmissionNewBikeSerializer()
    build = SubmissionNewBuildSerializer()


class SubmissionSerializer(serializers.ModelSerializer):
    """신청서 직렬화기."""

    bike = BikeSerializer(read_only=True)
    build = BikeBuildSerializer(read_only=True)
    story_blocks = serializers.ListField(child=StoryBlockSerializer(), allow_empty=False)
    build_snapshot = serializers.DictField(allow_empty=True, required=False)
    build_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    new_build_payload = SubmissionNewBuildPayloadSerializer(required=False, write_only=True)
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
            "build_id",
            "new_build_payload",
            "status",
            "reason_code",
            "reason_detail",
            "created_at",
            "updated_at",
            "images",
        ]
        read_only_fields = (
            "id",
            "user",
            "status",
            "reason_code",
            "reason_detail",
            "created_at",
            "updated_at",
            "images",
        )
        extra_kwargs = {
            "build_id": {"write_only": True},
            "new_build_payload": {"write_only": True},
        }

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

        question_set = load_question_set()
        required_groups = question_set.metadata.get("require_one_from_groups", [])
        if required_groups:
            answered_ids = {item["question_id"] for item in value if item.get("question_id")}
            for group_key in required_groups:
                group_question_ids = {
                    question["id"]
                    for question in question_set.groups.get(group_key, [])
                    if question.get("id")
                }
                if group_question_ids and not (answered_ids & group_question_ids):
                    label = question_set.group_labels.get(group_key, group_key)
                    raise serializers.ValidationError(
                        {"story_blocks": f"'{label}' 섹션의 질문 중 최소 1개는 답변이 필요합니다."}
                    )
        return value

    def validate_build_snapshot(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("빌드 스냅샷은 딕셔너리 형식이어야 합니다.")
        return value

    def validate(self, attrs):
        build_id = attrs.get("build_id")
        new_build_payload = attrs.get("new_build_payload")
        build_snapshot = attrs.get("build_snapshot")

        if build_id and new_build_payload:
            raise serializers.ValidationError(
                {"non_field_errors": "build_id와 new_build_payload 중 하나만 선택해 주세요."}
            )
        if not build_id and not new_build_payload and build_snapshot is None:
            raise serializers.ValidationError(
                {"build_snapshot": "build_id 또는 new_build_payload가 없으면 build_snapshot을 제공해야 합니다."}
            )
        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        build_id = validated_data.pop("build_id", None)
        new_build_payload = validated_data.pop("new_build_payload", None)
        provided_snapshot = validated_data.pop("build_snapshot", None)

        with transaction.atomic():
            build: BikeBuild | None = None

            if build_id:
                build = (
                    BikeBuild.objects.select_related("base_bike")
                    .filter(pk=build_id, base_bike__owner_id=getattr(user, "id", None))
                    .first()
                )
                if not build:
                    raise serializers.ValidationError(
                        {"build_id": "본인 소유의 빌드만 선택할 수 있습니다."}
                    )
            elif new_build_payload:
                bike_data = new_build_payload.get("bike", {})
                build_data = new_build_payload.get("build", {})
                bike = Bike.objects.create(owner=user, **bike_data)
                build = BikeBuild.objects.create(base_bike=bike, **build_data)

            if build:
                validated_data["bike"] = build.base_bike
                validated_data["build"] = build
                validated_data["build_snapshot"] = build_to_snapshot(build)
            elif provided_snapshot is not None:
                validated_data["build_snapshot"] = provided_snapshot
            else:
                validated_data.setdefault("build_snapshot", {})

            return Submission.objects.create(user=user, **validated_data)

    def update(self, instance: Submission, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SubmissionCommentSerializer(serializers.Serializer):
    """상태 전이 시 코멘트를 전달하기 위한 기본 직렬화기."""

    comment = serializers.CharField(required=False, allow_blank=True)


class SubmissionRejectSerializer(serializers.Serializer):
    """반려 사유를 명시하는 직렬화기."""

    reason_code = serializers.ChoiceField(choices=SubmissionRejectionReason.choices, required=True)
    reason_detail = serializers.CharField(required=False, allow_blank=True)
