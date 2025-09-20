"""바이크 관련 API 뷰셋입니다."""
from __future__ import annotations

from rest_framework import permissions, viewsets

from .models import Bike
from .serializers import BikeSerializer


class BikeViewSet(viewsets.ModelViewSet):
    """회원의 자전거를 조회/수정/삭제할 수 있는 API."""

    serializer_class = BikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bike.objects.filter(owner=self.request.user).select_related("spec")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
