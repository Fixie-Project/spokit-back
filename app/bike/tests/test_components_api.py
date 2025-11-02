import uuid

import pytest
from rest_framework.test import APIClient

from app.bike.models import Bike, BikeBuild


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="tester@example.com",
        password="secret123",
        username="tester",
        nickname="tester",
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def bike(user):
    return Bike.objects.create(owner=user, frame_name="Affinity Lo Pro", is_public=True)


@pytest.mark.django_db
class TestBikeBuildCreate:
    endpoint = "/api/bike-builds/"

    def _payload(self, bike, components):
        return {
            "base_bike": str(bike.id),
            "title": "My build",
            "components": components,
            "note": "test",
            "is_public": True,
        }

    def test_success_with_list_components(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": ["Engine 11 Vortex"],
                "wheel": ["Phil Wood hub"],
                "drivetrain": ["Miche Primato crank"],
            },
        )

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 201
        data = response.data["data"]
        assert data["components"] == payload["components"]
        assert BikeBuild.objects.filter(base_bike=bike).count() == 1

    def test_promote_string_to_list(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": "Engine 11 Vortex",
                "wheel": ["Phil Wood hub"],
                "drivetrain": ["Miche Primato crank"],
            },
        )

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 201
        data = response.data["data"]
        assert data["components"]["frame_setup"] == ["Engine 11 Vortex"]

    def test_strip_blank_values(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": ["Engine"],
                "wheel": ["Phil Wood", " ", ""],
                "drivetrain": ["Miche"],
                "seat": ["Thomson", "  "],
            },
        )

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 201
        data = response.data["data"]
        assert data["components"]["wheel"] == ["Phil Wood"]
        assert data["components"]["seat"] == ["Thomson"]

    def test_reject_unknown_category(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": ["Engine"],
                "wheel": ["Phil Wood"],
                "drivetrain": ["Miche"],
                "unknown": ["mystery"],
            },
        )

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "unknown" in response.data["components"]

    def test_require_minimum_three_categories(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": ["Engine"],
                "wheel": ["Phil Wood"],
            },
        )

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "최소 3개" in str(response.data)

    def test_base_bike_must_exist(self, auth_client, bike):
        payload = self._payload(
            bike,
            {
                "frame_setup": ["Engine"],
                "wheel": ["Phil Wood"],
                "drivetrain": ["Miche"],
            },
        )
        payload["base_bike"] = str(uuid.uuid4())

        response = auth_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "base_bike" in response.data


@pytest.mark.django_db
def test_bike_public_list_query_count(auth_client, django_user_model, django_assert_num_queries):
    owner = django_user_model.objects.create_user(
        email="owner@example.com",
        password="secret123",
        username="owner",
        nickname="owner",
    )

    bikes = [
        Bike.objects.create(owner=owner, frame_name=f"Owner Bike {idx}", is_public=True)
        for idx in range(2)
    ]
    for bike in bikes:
        BikeBuild.objects.create(
            base_bike=bike,
            title="build",
            components={
                "frame_setup": ["Engine"],
                "wheel": ["Phil"],
                "drivetrain": ["Miche"],
            },
            is_public=True,
        )

    url = f"/api/users/{owner.id}/bikes/"

    with django_assert_num_queries(5):
        response = auth_client.get(url)

    assert response.status_code == 200
    assert len(response.data["data"]) == 2
