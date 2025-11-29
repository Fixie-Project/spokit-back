"""신청서 상태 전이 및 관련 서비스."""
from __future__ import annotations

from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from app.bike.models import Bike, BikeBuild
from app.user.models import Staff, User

from .models import Submission, SubmissionStatus, SubmissionStatusLog

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    SubmissionStatus.DRAFT: {SubmissionStatus.SUBMITTED},
    SubmissionStatus.SUBMITTED: {SubmissionStatus.IN_REVIEW, SubmissionStatus.REJECTED},
    SubmissionStatus.IN_REVIEW: {SubmissionStatus.APPROVED, SubmissionStatus.REJECTED},
    SubmissionStatus.APPROVED: {SubmissionStatus.POSTING, SubmissionStatus.REJECTED},
    SubmissionStatus.POSTING: {SubmissionStatus.PUBLISHED, SubmissionStatus.REJECTED},
    SubmissionStatus.REJECTED: {SubmissionStatus.RESUBMITTED},
    SubmissionStatus.RESUBMITTED: {SubmissionStatus.IN_REVIEW},
}


def build_to_snapshot(build: BikeBuild) -> dict:
    """빌드 객체를 신청서에 저장할 스냅샷 형태로 변환."""

    bike = build.base_bike
    return {
        "bike": {
            "id": str(bike.id),
            "name": bike.name,
            "frame_name": bike.frame_name,
            "is_public": bike.is_public,
        },
        "build": {
            "id": str(build.id),
            "title": build.title,
            "components": build.components,
            "note": build.note,
            "is_public": build.is_public,
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
