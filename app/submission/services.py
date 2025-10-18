"""신청서 상태 전이 및 관련 서비스."""
from __future__ import annotations

from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

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

    if to_status == SubmissionStatus.REJECTED and not comment:
        raise ValidationError({"comment": "반려 사유를 입력해 주세요."})

    changed_by_staff, changed_by_user = _resolve_actor(actor)
    if not changed_by_staff and not changed_by_user:
        raise ValidationError("상태 변경 주체가 존재해야 합니다.")

    with transaction.atomic():
        submission.status = to_status
        submission.save(update_fields=["status", "updated_at"])

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
