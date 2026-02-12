"""v2 스키마에 맞춘 신청서 직렬화기."""
from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from app.bike.models import Bike, BikeBuild
from app.bike.serializers import BikeBuildWriteSerializer

from .models import Submission, SubmissionRejectionReason
from .services import build_to_snapshot


class StoryBlockSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    question_text = serializers.CharField(required=False, allow_blank=True)
    answer = serializers.CharField()
    images = serializers.ListField(child=serializers.URLField(), required=False)


class SubmissionNewBikeSerializer(serializers.Serializer):
    """신규 빌드 생성 시 필요한 자전거 정보."""

    frame_name = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True)


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

    story_blocks = serializers.ListField(child=StoryBlockSerializer(), allow_empty=False)
    build_snapshot = serializers.DictField(allow_empty=True, required=False)
    rider_snapshot = serializers.DictField(read_only=True)
    build_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    new_build_payload = SubmissionNewBuildPayloadSerializer(required=False, write_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "user",
            "title",
            "build_snapshot",
            "story_blocks",
            "rider_snapshot",
            "build_id",
            "new_build_payload",
            "status",
            "reason_code",
            "reason_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "user",
            "status",
            "reason_code",
            "reason_detail",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "title": {"required": False, "allow_blank": True},
            "build_id": {"write_only": True},
            "new_build_payload": {"write_only": True},
        }

    def validate_story_blocks(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("스토리 블록은 리스트 형태여야 합니다.")
        if not value:
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

    def _compose_title(
        self,
        user,
        *,
        build: BikeBuild | None,
        build_snapshot: dict | None,
    ) -> str:
        nickname = getattr(user, "nickname", "") or getattr(user, "username", "") or "라이더"
        build_title = ""
        if build and build.title:
            build_title = build.title
        elif isinstance(build_snapshot, dict):
            build_info = build_snapshot.get("build", {}) if build_snapshot else {}
            build_title = build_info.get("title") or ""
            if not build_title:
                bike_info = build_snapshot.get("bike", {}) if build_snapshot else {}
                build_title = bike_info.get("frame_name") or build_snapshot.get("frame_name") or ""
        if not build_title:
            build_title = "내 빌드"
        return f"{nickname} - {build_title}"

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

            if not (validated_data.get("title") or "").strip():
                validated_data["title"] = self._compose_title(
                    user,
                    build=build,
                    build_snapshot=validated_data.get("build_snapshot"),
                )

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


class MessageSerializer(serializers.Serializer):
    """단순 메시지 래퍼."""

    message = serializers.CharField()


class SubmissionListItemSerializer(serializers.ModelSerializer):
    """신청서 목록용 요약."""

    bike_frame = serializers.SerializerMethodField()
    build_title = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "status",
            "bike_frame",
            "build_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_bike_frame(self, obj):
        if obj.build and getattr(obj.build, "base_bike", None):
            return obj.build.base_bike.frame_name
        if obj.bike:
            return obj.bike.frame_name
        snapshot = obj.build_snapshot or {}
        return (
            snapshot.get("bike", {}).get("frame_name")
            or snapshot.get("frame_name")
            or None
        )

    def get_build_title(self, obj):
        if obj.build:
            return obj.build.title
        snapshot = obj.build_snapshot or {}
        return snapshot.get("build", {}).get("title") or snapshot.get("build_title") or None


class SubmissionListDataSerializer(serializers.Serializer):
    """신청서 목록 응답의 data 영역."""

    count = serializers.IntegerField()
    results = SubmissionListItemSerializer(many=True)


class SubmissionListResponseSerializer(MessageSerializer):
    """신청서 목록 래퍼."""

    data = SubmissionListDataSerializer()


class SubmissionDetailResponseSerializer(MessageSerializer):
    """단일 신청서 래퍼."""

    data = SubmissionSerializer()


class QuestionSetResponseSerializer(serializers.Serializer):
    """질문 세트 응답 데이터."""

    version = serializers.CharField()
    title = serializers.CharField(required=False)
    subtitle = serializers.CharField(required=False)
    group_labels = serializers.DictField(child=serializers.CharField())
    sections = serializers.DictField(child=serializers.DictField(), required=False)
    cta = serializers.DictField(required=False)
    helper = serializers.DictField(required=False)
    share = serializers.DictField(required=False)
    non_selectable_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    groups = serializers.DictField(child=serializers.ListField(child=serializers.DictField()))
    required_ids = serializers.ListField(child=serializers.CharField(), required=False)


class QuestionSetMessageSerializer(MessageSerializer):
    """질문 세트 래퍼."""

    data = QuestionSetResponseSerializer()


class SubmissionValidationDataSerializer(serializers.Serializer):
    """제출 가능 여부 응답 데이터."""

    submittable = serializers.BooleanField()
    missing_required_ids = serializers.ListField(child=serializers.CharField(), required=False)
    missing_groups = serializers.ListField(child=serializers.CharField(), required=False)
    need_more_optional_answers = serializers.IntegerField()


class SubmissionValidationResponseSerializer(MessageSerializer):
    """제출 가능 여부 응답 래퍼."""

    data = SubmissionValidationDataSerializer()
