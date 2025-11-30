"""Core-level utility API views (e.g., image metadata registration)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response

from .serializers import BaseImageUploadSerializer


class BaseImageUploadView(views.APIView):
    """Register an already-uploaded image (e.g., S3) as BaseImage."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Images"],
        summary="이미지 메타데이터 등록",
        description="S3 등에 업로드된 이미지의 메타데이터(url, s3_key 등)를 등록하고 id를 반환합니다.",
        request=BaseImageUploadSerializer,
        responses=BaseImageUploadSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = BaseImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

