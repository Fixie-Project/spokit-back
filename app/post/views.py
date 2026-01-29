"""Deprecated: use app.post.api instead."""
from __future__ import annotations

from .api import (
    PostLikeToggleAPIView,
    CommentCreateAPIView,
    CommentDetailAPIView,
)

__all__ = [
    "PostLikeToggleAPIView",
    "CommentCreateAPIView",
    "CommentDetailAPIView",
]
