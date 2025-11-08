"""submission 앱 테스트 자리입니다."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from app.submission.models import Submission, SubmissionStatus, SubmissionRejectionReason
from app.user.models import Staff, StaffRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def applicant(django_user_model):
    return django_user_model.objects.create_user(
        email="applicant@example.com",
        password="secret123",
        username="applicant",
        nickname="applicant",
    )


@pytest.fixture
def editor(django_user_model):
    user = django_user_model.objects.create_user(
        email="editor@example.com",
        password="secret123",
        username="editor",
        nickname="editor",
    )
    Staff.objects.create(user=user, role=StaffRole.EDITOR)
    return user


@pytest.fixture
def submission(applicant):
    return Submission.objects.create(
        user=applicant,
        title="My Story",
        story_blocks=[],
        build_snapshot={},
    )


@pytest.mark.django_db
def test_reject_requires_reason_code(api_client, editor, submission):
    api_client.force_authenticate(user=editor)
    url = reverse("submission-workflow-reject", kwargs={"pk": submission.pk})

    response = api_client.post(url, data={}, format="json")

    assert response.status_code == 400
    assert "reason_code" in response.data


@pytest.mark.django_db
def test_reject_with_reason_stores_fields(api_client, editor, submission):
    api_client.force_authenticate(user=editor)
    url = reverse("submission-workflow-reject", kwargs={"pk": submission.pk})
    payload = {
        "reason_code": SubmissionRejectionReason.PHOTO_ISSUE,
        "reason_detail": "이미지 해상도가 낮습니다.",
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == SubmissionStatus.REJECTED
    assert data["reason_code"] == SubmissionRejectionReason.PHOTO_ISSUE
    assert data["reason_detail"] == payload["reason_detail"]

    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.REJECTED
    assert submission.reason_code == SubmissionRejectionReason.PHOTO_ISSUE
    assert submission.reason_detail == payload["reason_detail"]

    log = submission.status_logs.latest("changed_at")
    assert log.to_status == SubmissionStatus.REJECTED
    assert payload["reason_detail"] in log.comment
