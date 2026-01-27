"""URL patterns for bike app."""
from __future__ import annotations

from django.urls import path

from .api import (
    BikeBuildListCreateView,
    BikeBuildDetailView,
    BikeBuildArchiveListView,
    MyBikeBuildDetailView,
    BikeDetailView,
    BikeListCreateView,
)


urlpatterns = [
    # 내 자전거/빌드 전용
    path("me/bikes/", BikeListCreateView.as_view(), name="my-bike-list"),
    path("me/bikes/<uuid:bike_id>/", BikeDetailView.as_view(), name="my-bike-detail"),
    path("me/bike-builds/", BikeBuildListCreateView.as_view(), name="my-bike-build-list"),
    path("me/bike-builds/<uuid:build_id>/", MyBikeBuildDetailView.as_view(), name="my-bike-build-detail"),

    path("bike-builds/<uuid:build_id>/", BikeBuildDetailView.as_view(), name="bike-build-detail"),
    path("public/bike-builds/", BikeBuildArchiveListView.as_view(), name="bike-build-archive"),
]
