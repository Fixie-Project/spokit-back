"""Authentication and profile routes."""
from django.contrib.auth import views as auth_views
from django.urls import path

from .views import ProfileView, SignupView

app_name = "user"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="user/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("signup/", SignupView.as_view(), name="signup"),
]
