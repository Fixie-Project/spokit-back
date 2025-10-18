"""사용자 관련 API 라우팅."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "user"

urlpatterns = [
    path("auth/jwt/create/", views.EmailTokenObtainPairAPIView.as_view(), name="jwt-create"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    path("auth/google/", views.GoogleOAuthLoginAPIView.as_view(), name="oauth-google"),
    path("me/submissions/", views.UserSubmissionListAPIView.as_view(), name="submissions"),
    path("me/submissios/", views.UserSubmissionListAPIView.as_view(), name="submissions-legacy"),
    path("me/submissions/<uuid:pk>/", views.UserSubmissionDetailAPIView.as_view(), name="submission-detail"),
    path("me/profile/", views.UserProfileAPIView.as_view(), name="profile"),
    path("me/profile/stats/", views.UserProfileSummaryAPIView.as_view(), name="profile-stats"),
]
