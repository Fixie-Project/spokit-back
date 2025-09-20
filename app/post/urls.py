"""URL routes for the post app."""
from django.urls import path

from . import views

app_name = "post"

urlpatterns = [
    path("", views.PostListView.as_view(), name="list"),
    path("posts/new/", views.PostCreateView.as_view(), name="create"),
    path("posts/<slug:slug>/edit/", views.PostUpdateView.as_view(), name="edit"),
    path("posts/autosave/", views.SubmissionDraftAutosaveView.as_view(), name="submission_autosave"),
    path("tags/<slug:slug>/", views.TaggedPostListView.as_view(), name="tagged"),
    path("posts/<slug:slug>/", views.PostDetailView.as_view(), name="detail"),
    path("posts/<slug:slug>/like/", views.LikeToggleView.as_view(), name="toggle_like"),
    path("submit/", views.SubmissionCreateView.as_view(), name="submit"),
    path("gear-calc/", views.GearCalculatorView.as_view(), name="gear_calc"),
]
