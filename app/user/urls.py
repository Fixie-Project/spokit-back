"""사용자 인증과 프로필 관련 URL 패턴입니다."""
from django.urls import path

from .views import (
    CustomLoginView,
    LogoutRedirectView,
    ProfileView,
    SignupView,
    SubmissionUpdateView,
)

app_name = "user"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutRedirectView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("signup/", SignupView.as_view(), name="signup"),
    path(
        "submissions/<int:pk>/edit/",
        SubmissionUpdateView.as_view(),
        name="submission_edit",
    ),
]
