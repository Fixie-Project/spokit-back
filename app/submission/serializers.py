"""소개 신청 API 직렬화 도구입니다."""
from __future__ import annotations

from rest_framework import serializers

from app.bike.models import Bike
from app.bike.serializers import BikeSerializer

from .models import Submission, SubmissionImage, SubmissionStatus
from .questions import DEFAULT_QUESTION_VERSION, load_question_set

class SubmissionImageSerializer(serializers.ModelSerializer):
    """소개 신청에 첨부된 이미지를 직렬화합니다."""

    class Meta:
        model = SubmissionImage
        fields = ["id", "image"]
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    """소개 신청과 관련된 정보를 직렬화합니다."""

    MIN_BLOCKS = 1

    bike = BikeSerializer(required=False)
    sns_links = serializers.ListField(child=serializers.CharField(), required=False)
    required_question_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    story_blocks = serializers.ListField(child=serializers.DictField(), required=False)
    external_story_url = serializers.URLField(required=False, allow_blank=True)
    question_version = serializers.CharField(required=False, allow_blank=False)
    images = SubmissionImageSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "user",
            "title",
            "required_question_ids",
            "story_blocks",
            "external_story_url",
            "blocks_count",
            "sns_links",
            "status",
            "rejection_reason",
            "draft_data",
            "reviewed_at",
            "reviewer",
            "result_post",
            "created_at",
            "bike",
            "images",
            "question_version",
        ]
        read_only_fields = (
            "id",
            "blocks_count",
            "status",
            "rejection_reason",
            "draft_data",
            "reviewed_at",
            "reviewer",
            "result_post",
            "created_at",
            "user",
            "images",
        )

    def _get_question_set(self):
        if hasattr(self, "_question_set"):
            return self._question_set
        if self.instance:
            version = self.instance.question_version or DEFAULT_QUESTION_VERSION
        else:
            version = self.initial_data.get("question_version") if hasattr(self, "initial_data") else None
            if not version:
                version = DEFAULT_QUESTION_VERSION
        self._question_set = load_question_set(version)
        return self._question_set

    def validate_required_question_ids(self, value: list[str] | None):
        question_set = self._get_question_set()
        lookup = question_set.lookup
        if value is None:
            cleaned_ids: list[str] = []
        elif not isinstance(value, list):
            raise serializers.ValidationError("필수 질문 ID는 리스트 형태여야 합니다.")
        else:
            cleaned_ids = []
            seen = set()
            for idx, item in enumerate(value):
                if not isinstance(item, str):
                    raise serializers.ValidationError(
                        f"필수 질문 ID 목록의 {idx + 1}번째 항목이 문자열이 아닙니다."
                    )
                question_id = item.strip()
                if not question_id:
                    raise serializers.ValidationError(
                        f"필수 질문 ID 목록의 {idx + 1}번째 항목이 비어 있습니다."
                    )
                if question_id not in lookup:
                    raise serializers.ValidationError(
                        f"알 수 없는 질문 ID({question_id})가 포함되어 있습니다."
                    )
                if question_id in seen:
                    continue
                cleaned_ids.append(question_id)
                seen.add(question_id)

        self._validated_required_question_ids = cleaned_ids
        return cleaned_ids

    def validate_external_story_url(self, value: str | None) -> str:
        return (value or "").strip()

    def _should_require_story_blocks(self) -> bool:
        raw_url = self.initial_data.get("external_story_url") if hasattr(self, "initial_data") else None
        if isinstance(raw_url, str) and raw_url.strip():
            return False
        if self.instance and getattr(self.instance, "external_story_url", ""):
            return False
        return True

    def _get_required_ids_for_story_blocks(self) -> set[str]:
        if hasattr(self, "_validated_required_question_ids"):
            return set(self._validated_required_question_ids)
        question_set = self._get_question_set()
        if self.instance and isinstance(self.instance.required_question_ids, list):
            return {qid for qid in self.instance.required_question_ids if qid in question_set.lookup}
        return set()

    def validate_story_blocks(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("스토리 블록은 리스트 형태여야 합니다.")

        requires_story = self._should_require_story_blocks()

        if not value:
            if requires_story:
                raise serializers.ValidationError("최소 1개의 질문에 답변해 주세요.")
            return []

        if requires_story and len(value) < self.MIN_BLOCKS:
            raise serializers.ValidationError("최소 1개의 질문에 답변해 주세요.")

        seen_required = set()
        answered_ids = set()
        cleaned_blocks: list[dict] = []

        question_set = self._get_question_set()
        lookup = question_set.lookup
        custom_ids = question_set.custom_ids

        for idx, raw_block in enumerate(value):
            if not isinstance(raw_block, dict):
                raise serializers.ValidationError(f"{idx + 1}번째 블록이 올바른 형식이 아닙니다.")

            block = dict(raw_block)
            question_id = block.get("question_id")
            if not question_id:
                raise serializers.ValidationError(f"{idx + 1}번째 블록에 question_id가 없습니다.")

            question_def = lookup.get(question_id)
            if question_def is None:
                raise serializers.ValidationError(f"알 수 없는 질문 ID({question_id})입니다.")

            question_text = (block.get("question_text") or "").strip()
            if question_id in custom_ids:
                if not question_text:
                    raise serializers.ValidationError(
                        f"{idx + 1}번째 블록의 question_text를 입력해 주세요."
                    )
            else:
                block["question_text"] = question_def["text"]

            answer = block.get("answer")
            if answer is None or (isinstance(answer, str) and not answer.strip()):
                raise serializers.ValidationError(
                    f"{idx + 1}번째 블록의 answer가 비어 있습니다."
                )
            answered_ids.add(question_id)

            images = block.get("images") or []
            if not isinstance(images, list):
                raise serializers.ValidationError(
                    f"{idx + 1}번째 블록의 images는 리스트여야 합니다."
                )
            if len(images) > 3:
                raise serializers.ValidationError(
                    f"{idx + 1}번째 블록에는 최대 3개의 이미지만 첨부할 수 있습니다."
                )

            normalized_images: list[dict[str, str]] = []
            for img_idx, image in enumerate(images):
                if isinstance(image, str):
                    url = image.strip()
                elif isinstance(image, dict):
                    url = (image.get("url") or "").strip()
                else:
                    raise serializers.ValidationError(
                        f"{idx + 1}번째 블록의 {img_idx + 1}번째 이미지 형식이 올바르지 않습니다."
                    )
                if not url:
                    raise serializers.ValidationError(
                        f"{idx + 1}번째 블록의 {img_idx + 1}번째 이미지 URL이 비어 있습니다."
                    )
                normalized_images.append({"url": url})
            block["images"] = normalized_images

            if question_def.get("required"):
                seen_required.add(question_id)

            cleaned_blocks.append(block)

        if requires_story:
            required_ids = question_set.required_ids
            missing = required_ids - seen_required
            if missing:
                raise serializers.ValidationError(
                    f"필수 질문({', '.join(sorted(missing))})에 대한 답변이 필요합니다."
                )

        if cleaned_blocks:
            required_ids = self._get_required_ids_for_story_blocks()
            missing_required_ids = required_ids - answered_ids
            if missing_required_ids:
                raise serializers.ValidationError(
                    f"필수 질문({', '.join(sorted(missing_required_ids))})에 대한 답변이 필요합니다."
                )

        return cleaned_blocks

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        question_set = self._get_question_set()

        story_blocks = attrs.get("story_blocks")
        if story_blocks is None and self.instance is not None:
            story_blocks = self.instance.story_blocks or []
        external_story_url = attrs.get("external_story_url")
        if external_story_url is None and self.instance is not None:
            external_story_url = self.instance.external_story_url or ""

        has_story_blocks = bool(story_blocks)
        has_external_story = bool((external_story_url or "").strip())
        if not has_story_blocks and not has_external_story:
            raise serializers.ValidationError(
                "스토리 블록을 입력하거나 외부 링크를 첨부해 주세요."
            )

        attrs["question_version"] = question_set.version
        selected_ids = list(attrs.get("required_question_ids", []))
        selected_set = set(selected_ids)
        for required_id in question_set.required_ids:
            if required_id not in selected_set:
                selected_ids.append(required_id)
                selected_set.add(required_id)
        attrs["required_question_ids"] = selected_ids
        self._validated_required_question_ids = selected_ids
        return attrs

    def create(self, validated_data: dict):
        version = validated_data.pop("question_version", DEFAULT_QUESTION_VERSION)
        bike_data = validated_data.pop("bike", None)
        submission = Submission.objects.create(question_version=version, **validated_data)
        if bike_data:
            bike_data.setdefault("name", submission.title or f"Submission {submission.pk}")
            bike_serializer = BikeSerializer(data=bike_data)
            bike_serializer.is_valid(raise_exception=True)
            bike = bike_serializer.save(owner=submission.user)
            submission.bike = bike
            submission.save(update_fields=["bike"])
        else:
            submission.ensure_bike(owner=submission.user, name=submission.title)
        return submission

    def update(self, instance: Submission, validated_data: dict):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not (user and user.is_staff):
            allowed_statuses = {SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW}
            if instance.status not in allowed_statuses:
                raise serializers.ValidationError(
                    "접수 중이거나 대기 중인 신청서만 수정할 수 있습니다."
                )
        validated_data.pop("question_version", None)
        bike_data = validated_data.pop("bike", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if bike_data is not None:
            bike_data.setdefault("name", instance.title or f"Submission {instance.pk}")
            if instance.bike:
                bike_serializer = BikeSerializer(instance=instance.bike, data=bike_data, partial=True)
                bike_serializer.is_valid(raise_exception=True)
                bike_serializer.save()
            else:
                bike_serializer = BikeSerializer(data=bike_data)
                bike_serializer.is_valid(raise_exception=True)
                bike = bike_serializer.save(owner=instance.user)
                instance.bike = bike
                instance.save(update_fields=["bike"])
        else:
            instance.ensure_bike(owner=instance.user, name=instance.title)
        return instance
