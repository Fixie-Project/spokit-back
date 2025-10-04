from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("submissions/<int:pk>/", views.SubmissionDetailView.as_view(), name="submission_detail"),
]
