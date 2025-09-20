"""Project level URL configuration."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.bike.api import BikeViewSet
from app.submission.api import SubmissionViewSet

router = DefaultRouter()
router.register(r"bikes", BikeViewSet, basename="bike")
router.register(r"submissions", SubmissionViewSet, basename="submission")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("app.post.urls")),
    path("users/", include("app.user.urls")),
    path("api/", include(router.urls)),
]
