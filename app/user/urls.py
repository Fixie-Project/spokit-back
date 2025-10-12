"""User API routes."""
from django.urls import path

from . import views

app_name = "user"

urlpatterns = [
    path("me/submissions/", views.UserSubmissionListAPIView.as_view(), name="submissions"),
    path("me/submissions/<int:pk>/", views.UserSubmissionDetailAPIView.as_view(), name="submission-detail"),
    path("me/profile/", views.UserProfileSummaryAPIView.as_view(), name="profile"),
]
