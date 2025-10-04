"""바이크 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from .models import Bike
from .serializers import BikeSerializer


@extend_schema_view(
    list=extend_schema(tags=["Bikes"], summary="바이크 목록 조회"),
    retrieve=extend_schema(tags=["Bikes"], summary="바이크 상세 조회"),
    create=extend_schema(tags=["Bikes"], summary="바이크 등록"),
    update=extend_schema(tags=["Bikes"], summary="바이크 전체 수정"),
    partial_update=extend_schema(tags=["Bikes"], summary="바이크 부분 수정"),
    destroy=extend_schema(tags=["Bikes"], summary="바이크 삭제"),
)
class BikeViewSet(viewsets.ModelViewSet):
    """회원의 자전거를 조회/수정/삭제할 수 있는 API."""

    serializer_class = BikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bike.objects.filter(owner=self.request.user).select_related("spec")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
