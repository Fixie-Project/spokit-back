"""Studio API routes."""
from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("dashboard/", views.StudioDashboardAPIView.as_view(), name="dashboard"),
    path("submissions/<uuid:pk>/", views.StudioSubmissionDetailAPIView.as_view(), name="submission-detail"),
    path("staff/<uuid:pk>/", views.StaffDetailAPIView.as_view(), name="staff-detail"),
]
