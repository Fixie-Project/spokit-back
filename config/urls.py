"""Project level URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("app.post.urls")),
    path("users/", include("app.user.urls")),
]
