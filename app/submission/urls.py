from django.urls import path

from . import views

app_name = "submission"

urlpatterns = [
    path("submit/", views.SubmissionCreateView.as_view(), name="submit"),
]
