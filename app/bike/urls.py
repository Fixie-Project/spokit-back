"""URL patterns for bike app."""
from __future__ import annotations

from django.urls import path

from .api import (
    BikeBuildByBikeListView,
    BikeBuildListCreateView,
    BikeBuildDetailView,
    BikeBuildArchiveListView,
    BikeBuildPublicListView,
    BikeDetailView,
    BikeListCreateView,
    BikeOwnerPublicListAPIView,
    BikePublicArchiveListAPIView,
)


urlpatterns = [
    # 내 자전거/빌드 전용 에일리어스
    path("me/bikes/", BikeListCreateView.as_view(), name="my-bike-list"),
    path("me/bikes/<uuid:bike_id>/", BikeDetailView.as_view(), name="my-bike-detail"),
    path("me/bike-builds/", BikeBuildListCreateView.as_view(), name="my-bike-build-list"),
    path("me/bike-builds/<uuid:build_id>/", BikeBuildDetailView.as_view(), name="my-bike-build-detail"),

    path("bikes/", BikeListCreateView.as_view(), name="bike-list"),
    path("bikes/<uuid:bike_id>/", BikeDetailView.as_view(), name="bike-detail"),
    path("bikes/<uuid:bike_id>/builds/", BikeBuildByBikeListView.as_view(), name="bike-build-list-by-bike"),
    path("bike-builds/", BikeBuildListCreateView.as_view(), name="bike-build-list"),
    path("bike-builds/<uuid:build_id>/", BikeBuildDetailView.as_view(), name="bike-build-detail"),
    path("public/bike-builds/", BikeBuildArchiveListView.as_view(), name="bike-build-archive"),
    path("public/bikes/", BikePublicArchiveListAPIView.as_view(), name="bike-public-archive"),
    path("users/<uuid:user_id>/bikes/", BikeOwnerPublicListAPIView.as_view(), name="bike-user-public"),
    path(
        "users/<uuid:user_id>/bike-builds/",
        BikeBuildPublicListView.as_view(),
        name="bike-user-builds",
    ),
]
