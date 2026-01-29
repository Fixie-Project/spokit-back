"""Deprecated: use app.user.api instead."""
from __future__ import annotations

from .api import (
    UserProfileSummaryAPIView,
    UserProfileAPIView,
    EmailTokenObtainPairAPIView,
    PublicUserProfileAPIView,
    GoogleOAuthLoginAPIView,
)

__all__ = [
    "UserProfileSummaryAPIView",
    "UserProfileAPIView",
    "EmailTokenObtainPairAPIView",
    "PublicUserProfileAPIView",
    "GoogleOAuthLoginAPIView",
]
