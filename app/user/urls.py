"""사용자 관련 API 라우팅."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from app.submission.api import UserSubmissionDetailAPIView, UserSubmissionListAPIView

app_name = "user"

urlpatterns = [
    # JWT 인증 엔드포인트 (이메일/비밀번호 로그인 비활성화)
    # path("auth/jwt/create/", views.EmailTokenObtainPairAPIView.as_view(), name="jwt-create"),
    # path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    
    # OAuth2 인증 엔드포인트
    path("auth/google/", views.GoogleOAuthLoginAPIView.as_view(), name="oauth-google"),
    
    # 본인 정보 엔드포인트
    path("me/profile/", views.UserProfileAPIView.as_view(), name="profile"),
    path("me/profile/stats/", views.UserProfileSummaryAPIView.as_view(), name="profile-stats"),
    
    # 본인 신청서 엔드포인트
    path("me/submissions/", UserSubmissionListAPIView.as_view(), name="submissions"),
    path("me/submissions/<uuid:pk>/", UserSubmissionDetailAPIView.as_view(), name="submission-detail"),
    
    # (이전 경로는 app.bike.urls 로 이동)
]
