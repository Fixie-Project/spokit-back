import pytest
from rest_framework.test import APIClient

from app.bike.models import Bike, BikeBuild


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(
        email="owner@example.com",
        password="secret123",
        username="owner",
        nickname="owner",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        email="other@example.com",
        password="secret123",
        username="other",
        nickname="other",
    )


@pytest.fixture
def auth_client(api_client, owner):
    api_client.force_authenticate(user=owner)
    return api_client


@pytest.fixture
def build(owner):
    bike = Bike.objects.create(owner=owner, frame_name="Affinity")
    return BikeBuild.objects.create(
        base_bike=bike,
        title="Night Ride",
        components={
            "frame_setup": ["Affinity"],
            "wheel": ["H+Son"],
            "cockpit": ["Nitto"],
        },
        note="",
        is_public=True,
    )


@pytest.mark.django_db
def test_build_like_toggle(auth_client, build):
    url = f"/api/bike-builds/{build.id}/like/"

    response = auth_client.post(url)

    assert response.status_code == 200
    assert response.data["data"]["liked"] is True
    assert response.data["data"]["like_count"] == 1

    response = auth_client.post(url)

    assert response.status_code == 200
    assert response.data["data"]["liked"] is False
    assert response.data["data"]["like_count"] == 0


@pytest.mark.django_db
def test_like_denied_for_private_build(api_client, build, other_user):
    build.is_public = False
    build.save(update_fields=["is_public"])
    api_client.force_authenticate(user=other_user)
    url = f"/api/bike-builds/{build.id}/like/"

    response = api_client.post(url)

    assert response.status_code == 403
