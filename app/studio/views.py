"""Deprecated: use app.studio.api instead."""
from __future__ import annotations

from .api import (
    StudioDashboardAPIView,
    StudioSubmissionListAPIView,
    StudioSubmissionDetailAPIView,
    StudioSubmissionStatusAPIView,
    StaffDetailAPIView,
    StudioPostListAPIView,
    StudioPostDetailAPIView,
)

__all__ = [
    "StudioDashboardAPIView",
    "StudioSubmissionListAPIView",
    "StudioSubmissionDetailAPIView",
    "StudioSubmissionStatusAPIView",
    "StaffDetailAPIView",
    "StudioPostListAPIView",
    "StudioPostDetailAPIView",
]
