"""URL patterns for bike app."""
from __future__ import annotations

from django.urls import path

from .api import (
    BikeBuildByBikeListView,
    BikeBuildListCreateView,
    BikeBuildDetailView,
    BikeBuildPublicListView,
    BikeDetailView,
    BikeListCreateView,
    BikeOwnerPublicListAPIView,
    BikePublicArchiveListAPIView,
)


urlpatterns = [
    path("bikes/", BikeListCreateView.as_view(), name="bike-list"),
    path("bikes/<uuid:bike_id>/", BikeDetailView.as_view(), name="bike-detail"),
    path("bikes/<uuid:bike_id>/builds/", BikeBuildByBikeListView.as_view(), name="bike-build-list-by-bike"),
    path("bike-builds/", BikeBuildListCreateView.as_view(), name="bike-build-list"),
    path("bike-builds/<uuid:build_id>/", BikeBuildDetailView.as_view(), name="bike-build-detail"),
    path("public/bikes/", BikePublicArchiveListAPIView.as_view(), name="bike-public-archive"),
    path("users/<uuid:user_id>/bikes/", BikeOwnerPublicListAPIView.as_view(), name="bike-user-public"),
    path(
        "users/<uuid:user_id>/bike-builds/",
        BikeBuildPublicListView.as_view(),
        name="bike-user-builds",
    ),
]
