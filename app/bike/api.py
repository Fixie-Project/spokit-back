"""바이크 관련 API 뷰셋입니다."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Bike, BikeBuild
from .serializers import (
    BikeBuildDetailSerializer,
    BikeBuildSerializer,
    BikeBuildWriteSerializer,
    BikeSerializer,
)


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
        qs = Bike.objects.filter(owner=self.request.user).prefetch_related(
            "builds"
        )
        return qs.filter(is_public=True) if self.request.method == "GET" else qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=["Bike Builds"], summary="바이크 빌드 공개 목록 조회"),
    retrieve=extend_schema(tags=["Bike Builds"], summary="바이크 빌드 상세 조회"),
    create=extend_schema(
        tags=["Bike Builds"],
        summary="바이크 빌드 등록",
        examples=[
            OpenApiExample(
                name="Bike build payload",
                value={
                    "base_bike": "d6f2b8d4-5a1f-4f86-97be-0e8bbf08c888",
                    "title": "Commuter Setup",
                    "components": {
                        "wheel": {
                            "brand": "H Plus Son",
                            "model": "AT-25",
                            "details": {
                                "hub": {"brand": "Phil Wood", "model": "Low Flange"},
                                "tire": {"brand": "Continental", "model": "Gatorskin"},
                            },
                        },
                        "drivetrain": {
                            "brand": "SRAM",
                            "model": "Omnium",
                            "details": {
                                "chain": "Izumi Super Toughness",
                            },
                        },
                    },
                    "note": "도심 출퇴근용 세팅",
                },
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(tags=["Bike Builds"], summary="바이크 빌드 전체 수정"),
    partial_update=extend_schema(tags=["Bike Builds"], summary="바이크 빌드 부분 수정"),
    destroy=extend_schema(tags=["Bike Builds"], summary="바이크 빌드 삭제"),
)
class BikeBuildViewSet(viewsets.ModelViewSet):
    """회원이 자전거 빌드를 관리할 수 있는 API."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = BikeBuild.objects.filter(base_bike__owner=self.request.user).select_related("base_bike")
        if self.action in {"list", "retrieve"}:
            qs = qs.filter(is_public=True, base_bike__is_public=True)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BikeBuildSerializer
        if self.action == "retrieve":
            return BikeBuildDetailSerializer
        return BikeBuildWriteSerializer

    def perform_create(self, serializer):
        base_bike = serializer.validated_data["base_bike"]
        if base_bike.owner != self.request.user:
            raise PermissionDenied("본인 자전거에만 빌드를 추가할 수 있습니다.")
        serializer.save()

    def perform_update(self, serializer):
        base_bike = serializer.validated_data.get("base_bike", serializer.instance.base_bike)
        if base_bike.owner != self.request.user:
            raise PermissionDenied("본인 자전거에만 빌드를 수정할 수 있습니다.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.base_bike.owner != self.request.user:
            raise PermissionDenied("본인 자전거에만 빌드를 삭제할 수 있습니다.")
        instance.delete()

    @extend_schema(responses=BikeBuildSerializer(many=True), tags=["Bike Builds"], summary="내 빌드 전체 조회")
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="mine")
    def list_all_my_builds(self, request):
        """로그인 사용자의 모든 빌드를 공개 여부와 관계없이 반환."""

        queryset = BikeBuild.objects.filter(base_bike__owner=request.user).select_related("base_bike")
        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
