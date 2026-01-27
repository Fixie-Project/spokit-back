"""신청서 상태 전이 및 관련 서비스."""
from __future__ import annotations

from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from app.bike.models import Bike, BikeBuild
from app.user.models import Staff, User

from .models import Submission, SubmissionStatus, SubmissionStatusLog
from app.post.models import _build_rider_snapshot

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    SubmissionStatus.DRAFT: {SubmissionStatus.SUBMITTED},
    SubmissionStatus.SUBMITTED: {SubmissionStatus.IN_REVIEW, SubmissionStatus.REJECTED},
    SubmissionStatus.IN_REVIEW: {SubmissionStatus.APPROVED, SubmissionStatus.REJECTED},
    SubmissionStatus.APPROVED: {SubmissionStatus.PUBLISHED},
    SubmissionStatus.REJECTED: {SubmissionStatus.RESUBMITTED},
    SubmissionStatus.RESUBMITTED: {SubmissionStatus.IN_REVIEW},
}


def build_to_snapshot(build: BikeBuild) -> dict:
    """빌드 객체를 신청서에 저장할 스냅샷 형태로 변환."""

    bike = build.base_bike
    main_image = build.main_image
    gallery = getattr(build, "images", [])
    gallery_items = gallery.all() if hasattr(gallery, "all") else (gallery or [])
    return {
        "bike": {
            "id": str(bike.id),
            "name": bike.name,
            "frame_name": bike.frame_name,
        },
        "build": {
            "id": str(build.id),
            "title": build.title,
            "components": build.components,
            "note": build.note,
            "is_public": build.is_public,
            "main_image": (
                {
                    "id": str(main_image.id),
                    "url": main_image.url,
                    "width": main_image.width,
                    "height": main_image.height,
                }
                if main_image
                else None
            ),
            "images": [
                {
                    "id": str(item.image_id),
                    "url": item.image.url,
                    "width": item.image.width,
                    "height": item.image.height,
                    "order": item.order,
                    "caption": item.caption,
                }
                for item in gallery_items
            ],
        },
    }


def _resolve_actor(user: Optional[User]) -> tuple[Optional[Staff], Optional[User]]:
    """사용자/운영진 객체를 로깅용으로 분기."""

    if user is None:
        return None, None
    try:
        staff_profile = user.staff_profile  # type: ignore[attr-defined]
    except (AttributeError, Staff.DoesNotExist):
        staff_profile = None
    if staff_profile:
        return staff_profile, None
    return None, user


def change_submission_status(
    submission: Submission,
    *,
    to_status: str,
    actor: User,
    comment: str = "",
    reason_code: str | None = None,
    reason_detail: str = "",
) -> Submission:
    """신청서 상태를 전환하고 로그를 남깁니다."""

    from_status = submission.status
    if from_status == to_status:
        return submission

    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValidationError(
            {"status": f"{from_status} → {to_status} 전이는 허용되지 않습니다."}
        )

    if to_status == SubmissionStatus.REJECTED:
        if not reason_code:
            raise ValidationError({"reason_code": "반려 사유 코드를 선택해 주세요."})
        comment = comment or reason_detail or reason_code
    else:
        reason_code = ""
        reason_detail = ""

    changed_by_staff, changed_by_user = _resolve_actor(actor)
    if not changed_by_staff and not changed_by_user:
        raise ValidationError("상태 변경 주체가 존재해야 합니다.")

    with transaction.atomic():
        submission.status = to_status
        submission.reason_code = reason_code or ""
        submission.reason_detail = reason_detail or ""
        submission.save(update_fields=["status", "reason_code", "reason_detail", "updated_at"])

        log_kwargs = {
            "submission": submission,
            "from_status": from_status,
            "to_status": to_status,
            "comment": comment or "",
        }
        if changed_by_staff:
            log_kwargs["changed_by_staff"] = changed_by_staff
        else:
            log_kwargs["changed_by_user"] = changed_by_user
        SubmissionStatusLog.objects.create(**log_kwargs)

    return submission


def ensure_post_for_submission(submission: Submission, *, actor: User):
    """신청서로부터 게시글이 없으면 생성합니다."""

    if submission.post_id:
        return submission.post

    if not submission.bike_id or not submission.build_id:
        raise ValidationError({"submission": "게시글 생성에는 bike/build가 필요합니다."})

    from app.post.models import Post, PostStatus

    author_profile = getattr(actor, "staff_profile", None)

    base_slug = slugify(submission.title) or f"submission-{submission.pk}"
    slug = base_slug
    suffix = 1
    while Post.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    snapshot = submission.build_snapshot or {}
    bike_snapshot = snapshot.get("bike", {}) if isinstance(snapshot, dict) else {}

    frame_brand = bike_snapshot.get("frame_name") or getattr(submission.bike, "frame_name", "") or submission.title
    frame_type = bike_snapshot.get("frame_type", "")

    rider_snapshot = submission.rider_snapshot or _build_rider_snapshot(submission.user)

    return Post.objects.create(
        author=author_profile,
        submission=submission,
        bike=submission.bike,
        build=submission.build,
        build_snapshot=submission.build_snapshot or {},
        story_snapshot=submission.story_blocks or [],
        rider=submission.user,
        rider_snapshot=rider_snapshot,
        main_title=submission.title,
        sub_title=submission.title,
        content_md="",
        content_html="",
        content_json={},
        frame_brand=frame_brand,
        frame_type=frame_type,
        slug=slug,
        status=PostStatus.DRAFT,
    )
