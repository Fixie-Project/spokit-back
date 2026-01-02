"""API routes for post-related actions."""
from django.urls import path

from . import views

app_name = "post"

urlpatterns = [
    path("posts/<slug:slug>/like/", views.PostLikeToggleAPIView.as_view(), name="like"),
    path("posts/<slug:slug>/comments/", views.CommentCreateAPIView.as_view(), name="comment"),
    path("posts/<slug:slug>/comments/<uuid:comment_id>/", views.CommentDetailAPIView.as_view(), name="comment-detail"),
    # path("gear-calc/", views.GearCalculatorAPIView.as_view(), name="gear-calc"),
]
