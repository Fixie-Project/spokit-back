"""Project level URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from app.post.api import PostViewSet
from app.submission.api import (
    QuestionSetView,
    SubmissionModerationViewSet,
    SubmissionViewSet,
)
from app.core.api import BaseImageUploadView, BaseImageFileUploadView

router = DefaultRouter()
router.register(r"submissions", SubmissionViewSet, basename="submission")
router.register(
    r"submission-workflow",
    SubmissionModerationViewSet,
    basename="submission-workflow",
)
router.register(r"posts", PostViewSet, basename="post")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/", include("app.bike.urls")),
    path("api/", include("app.post.urls")),
    path("api/", include("app.user.urls")),
    path("api/studio/", include("app.studio.urls")),
    path("api/question-set/", QuestionSetView.as_view(), name="question-set"),
    path("api/images/", BaseImageUploadView.as_view(), name="image-upload"),
    path("api/images/upload/", BaseImageFileUploadView.as_view(), name="image-file-upload"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
