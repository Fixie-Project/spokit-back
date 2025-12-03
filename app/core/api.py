"""Core-level utility API views (e.g., image upload/metadata registration)."""
from __future__ import annotations

import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema
from PIL import Image
from rest_framework import permissions, status, views
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from app.core.responses import error_response

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


class BaseImageFileUploadView(views.APIView):
    """파일 업로드를 받아 S3(기본 스토리지)에 저장 후 BaseImage를 생성합니다."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    max_filesize = 10 * 1024 * 1024  # 10 MB
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    @extend_schema(
        tags=["Images"],
        summary="이미지 파일 업로드",
        description="multipart/form-data로 파일을 업로드하고 BaseImage 메타를 반환합니다.",
        responses=BaseImageUploadSerializer,
    )
    def post(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        if not upload:
            return error_response("파일을 첨부해 주세요.", status_code=status.HTTP_400_BAD_REQUEST)

        if upload.size > self.max_filesize:
            return error_response("최대 10MB까지 업로드할 수 있습니다.", status_code=status.HTTP_400_BAD_REQUEST)

        ext = (os.path.splitext(upload.name)[1] or "").lower().lstrip(".")
        if ext not in self.allowed_extensions:
            return error_response("허용되지 않은 파일 형식입니다.", status_code=status.HTTP_400_BAD_REQUEST)

        # 추출을 위해 읽고, 저장은 별도 버퍼로 처리
        buffer = upload.read()
        try:
            image = Image.open(BytesIO(buffer))
            width, height = image.size
        except Exception:  # pragma: no cover - PIL 오류
            return error_response("이미지 파일을 읽을 수 없습니다.", status_code=status.HTTP_400_BAD_REQUEST)

        saved_name = default_storage.save(upload.name, ContentFile(buffer))
        url = default_storage.url(saved_name)

        obj = BaseImage.objects.create(
            url=url,
            s3_key=saved_name,
            width=width,
            height=height,
            filesize=upload.size,
        )
        return Response(BaseImageUploadSerializer(obj).data, status=status.HTTP_201_CREATED)
