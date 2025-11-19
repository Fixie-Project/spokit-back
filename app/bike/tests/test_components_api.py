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


@pytest.mark.django_db
def test_public_bike_archive_lists_all_public_bikes(api_client, django_user_model):
    owner1 = django_user_model.objects.create_user(
        email="archive1@example.com",
        password="secret123",
        username="archive1",
        nickname="archive1",
    )
    owner2 = django_user_model.objects.create_user(
        email="archive2@example.com",
        password="secret123",
        username="archive2",
        nickname="archive2",
    )

    bike_public = Bike.objects.create(owner=owner1, frame_name="Public Bike", is_public=True)
    Bike.objects.create(owner=owner2, frame_name="Private Bike", is_public=False)
    BikeBuild.objects.create(
        base_bike=bike_public,
        title="build",
        components={
            "frame_setup": ["Engine"],
            "wheel": ["Phil"],
            "drivetrain": ["Miche"],
        },
        is_public=True,
    )

    response = api_client.get("/api/public/bikes/")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["frame_name"] == "Public Bike"
    assert data[0]["build_names"] == ["build"]


@pytest.mark.django_db
def test_bike_detail_requires_authentication(api_client, user):
    bike = Bike.objects.create(owner=user, frame_name="Need Login", is_public=True)
    url = f"/api/bikes/{bike.id}/"

    response = api_client.get(url)
    assert response.status_code in {401, 403}

    api_client.force_authenticate(user=user)
    response = api_client.get(url)
    assert response.status_code == 200
