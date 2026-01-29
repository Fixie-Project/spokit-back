"""Studio API routes."""
from django.urls import path

from . import api as views

app_name = "studio"

urlpatterns = [
    path("dashboard/", views.StudioDashboardAPIView.as_view(), name="dashboard"),
    path("posts/", views.StudioPostListAPIView.as_view(), name="post-list"),
    path("posts/<slug:slug>/", views.StudioPostDetailAPIView.as_view(), name="post-detail"),
    path("submissions/", views.StudioSubmissionListAPIView.as_view(), name="submission-list"),
    path("submissions/<uuid:pk>/", views.StudioSubmissionDetailAPIView.as_view(), name="submission-detail"),
    path(
        "submissions/<uuid:pk>/status/",
        views.StudioSubmissionStatusAPIView.as_view(),
        name="submission-status",
    ),
    path("staff/<uuid:pk>/", views.StaffDetailAPIView.as_view(), name="staff-detail"),
]
