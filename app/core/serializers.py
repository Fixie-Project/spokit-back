"""Core utility serializers."""
from __future__ import annotations

from rest_framework import serializers

from .models import BaseImage


class BaseImageUploadSerializer(serializers.ModelSerializer):
    """Simple serializer for creating BaseImage records after upload."""

    class Meta:
        model = BaseImage
        fields = ["id", "url", "s3_key", "width", "height", "filesize"]
        read_only_fields = ("id",)

