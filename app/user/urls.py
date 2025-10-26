"""사용자 관련 API 라우팅."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from app.bike.api import BikeBuildPublicListView, BikeOwnerPublicListAPIView

from . import views

app_name = "user"

urlpatterns = [
    # JWT 인증 엔드포인트
    path("auth/jwt/create/", views.EmailTokenObtainPairAPIView.as_view(), name="jwt-create"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    
    # OAuth2 인증 엔드포인트
    path("auth/google/", views.GoogleOAuthLoginAPIView.as_view(), name="oauth-google"),
    
    # 본인 정보 엔드포인트
    path("me/profile/", views.UserProfileAPIView.as_view(), name="profile"),
    path("me/profile/stats/", views.UserProfileSummaryAPIView.as_view(), name="profile-stats"),
    
    # 본인 신청서 엔드포인트
    path("me/submissions/", views.UserSubmissionListAPIView.as_view(), name="submissions"),
    path("me/submissios/", views.UserSubmissionListAPIView.as_view(), name="submissions-legacy"),
    path("me/submissions/<uuid:pk>/", views.UserSubmissionDetailAPIView.as_view(), name="submission-detail"),
    
    # 타인 정보 엔드포인트
    path("users/<uuid:user_id>/bikes/", BikeOwnerPublicListAPIView.as_view(), name="user-bike-list"),
    path(
        "users/<uuid:user_id>/bike-builds/",
        BikeBuildPublicListView.as_view(),
        name="user-bikebuild-list",
    ),
]
