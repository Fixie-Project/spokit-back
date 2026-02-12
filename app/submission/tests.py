"""submission 앱 테스트 자리입니다."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from app.bike.models import Bike, BikeBuild
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
        story_blocks=[{"question_id": "intro_1", "answer": "intro"}],
        build_snapshot={"frame_name": "Frame"},
    )


@pytest.fixture
def bike(applicant):
    return Bike.objects.create(owner=applicant, frame_name="Affinity", name="My Bike")


@pytest.fixture
def build(bike):
    return BikeBuild.objects.create(
        base_bike=bike,
        title="Street",
        components={
            "frame_setup": ["Affinity"],
            "wheel": ["H+Son"],
            "cockpit": ["Nitto"],
        },
        note="",
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
    submission.status = SubmissionStatus.SUBMITTED
    submission.save(update_fields=["status"])
    api_client.force_authenticate(user=editor)
    url = reverse("submission-workflow-reject", kwargs={"pk": submission.pk})
    payload = {
        "reason_code": SubmissionRejectionReason.PHOTO_ISSUE,
        "reason_detail": "이미지 해상도가 낮습니다.",
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
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


@pytest.mark.django_db
def test_submit_requires_outro_group(api_client, applicant):
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-list")
    payload = {
        "title": "My Story",
        "build_snapshot": {"frame_name": "Midnight"},
        "story_blocks": [
            {"question_id": "me_1", "answer": "자기소개"},
            {"question_id": "final_1", "answer": "내 스포킷"},
            {"question_id": "intro_1", "answer": "입문 계기"},
            {"question_id": "prod_1", "answer": "조립 시작"},
            {"question_id": "exper_1", "answer": "첫 라이딩"},
        ],
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    submission_id = response.json()["data"]["id"]

    submit_url = reverse("submission-submit", kwargs={"pk": submission_id})
    submit_response = api_client.post(submit_url, format="json")

    assert submit_response.status_code == 400
    body = submit_response.json()
    assert body["code"] == "SUBMISSION_NOT_READY"
    assert body["data"]["missing_groups"] == ["outro"]
    assert body["data"]["need_more_optional_answers"] == 0


@pytest.mark.django_db
def test_submit_passes_when_requirements_met(api_client, applicant):
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-list")
    payload = {
        "title": "My Story",
        "build_snapshot": {"frame_name": "Midnight"},
        "story_blocks": [
            {"question_id": "me_1", "answer": "자기소개"},
            {"question_id": "final_1", "answer": "내 스포킷"},
            {"question_id": "intro_1", "answer": "입문 계기"},
            {"question_id": "prod_1", "answer": "조립 시작"},
            {"question_id": "outro_2", "answer": "좋은 라이딩"},
        ],
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    submission_id = response.json()["data"]["id"]

    submit_url = reverse("submission-submit", kwargs={"pk": submission_id})
    submit_response = api_client.post(submit_url, format="json")

    assert submit_response.status_code == 200
    data = submit_response.json()["data"]
    assert data["status"] == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_create_submission_with_existing_build(api_client, applicant, build):
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-list")

    payload = {
        "title": "With Build",
        "story_blocks": [
            {"question_id": "intro_1", "answer": "픽시 입문"},
            {"question_id": "outro_1", "answer": "끝"},
        ],
        "build_id": str(build.id),
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    body = response.json()["data"]
    assert "build" not in body
    assert "bike" not in body
    assert body["build_snapshot"]["build"]["id"] == str(build.id)
    assert body["build_snapshot"]["bike"]["frame_name"] == build.base_bike.frame_name


@pytest.mark.django_db
def test_create_submission_with_new_build_payload(api_client, applicant):
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-list")

    payload = {
        "title": "New Build",
        "story_blocks": [
            {"question_id": "intro_1", "answer": "처음"},
            {"question_id": "outro_1", "answer": "마무리"},
        ],
        "new_build_payload": {
            "bike": {"frame_name": "New Frame", "name": "Fresh"},
            "build": {
                "title": "Build Title",
                "components": {
                    "frame_setup": ["Frame"],
                    "wheel": ["Wheel"],
                    "cockpit": ["Bar"],
                },
                "note": "",
                "is_public": True,
            },
        },
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    body = response.json()["data"]
    assert "build" not in body
    assert "bike" not in body
    assert body["build_snapshot"]["build"]["title"] == "Build Title"
    assert body["build_snapshot"]["bike"]["frame_name"] == "New Frame"


@pytest.mark.django_db
def test_create_submission_auto_title(api_client, applicant):
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-list")
    payload = {
        "story_blocks": [
            {"question_id": "intro_1", "answer": "처음"},
        ],
        "build_snapshot": {"frame_name": "Midnight"},
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["title"] == "applicant - Midnight"


@pytest.mark.django_db
def test_patch_denied_when_submitted(api_client, applicant, submission):
    submission.status = SubmissionStatus.SUBMITTED
    submission.save()
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-detail", kwargs={"pk": submission.pk})

    response = api_client.patch(url, data={"title": "new"}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STATUS"


@pytest.mark.django_db
def test_delete_denied_when_in_review(api_client, applicant, submission):
    submission.status = SubmissionStatus.IN_REVIEW
    submission.save()
    api_client.force_authenticate(user=applicant)
    url = reverse("submission-detail", kwargs={"pk": submission.pk})

    response = api_client.delete(url)

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STATUS"

    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.IN_REVIEW
