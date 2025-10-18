"""바이크 관련 API 뷰셋입니다."""
from __future__ import annotations

from django.db.models import Prefetch, Q
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Bike, BikeBuild
from .serializers import (
    BikeBuildDetailSerializer,
    BikeBuildSerializer,
    BikeBuildWriteSerializer,
    BikePublicListSerializer,
    BikeSerializer,
)
from app.core.responses import error_response

SAFE_TRUE_VALUES = {"1", "true", "yes", "on"}


def _to_bool(value: str | None) -> bool:
    return str(value).lower() in SAFE_TRUE_VALUES if value is not None else False


@extend_schema_view(
    list=extend_schema(
        tags=["Bikes"],
        summary="내 자전거 목록 조회",
        parameters=[
            OpenApiParameter(
                name="owner",
                location=OpenApiParameter.QUERY,
                description="소유자 ID. 지정하면 해당 사용자의 공개 자전거나 본인인 경우 전체를 조회합니다.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="include_hidden",
                location=OpenApiParameter.QUERY,
                description="`true`로 지정하면 내 자전거를 비공개 포함하여 조회합니다.",
                required=False,
                type=bool,
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Bikes"], summary="바이크 상세 조회"),
    create=extend_schema(tags=["Bikes"], summary="바이크 등록"),
    update=extend_schema(tags=["Bikes"], summary="바이크 전체 수정"),
    partial_update=extend_schema(tags=["Bikes"], summary="바이크 부분 수정"),
    destroy=extend_schema(tags=["Bikes"], summary="바이크 삭제"),
)
class BikeViewSet(viewsets.ModelViewSet):
    """회원의 자전거를 조회/수정/삭제할 수 있는 API."""

    serializer_class = BikeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        owner_id = self.request.query_params.get("owner")
        include_hidden = _to_bool(self.request.query_params.get("include_hidden"))

        if owner_id:
            qs = Bike.objects.filter(owner_id=owner_id)
            if (
                include_hidden
                and self.request.user.is_authenticated
                and str(self.request.user.id) == str(owner_id)
            ):
                return qs.prefetch_related(
                    Prefetch(
                        "builds",
                        queryset=BikeBuild.objects.filter(base_bike__owner_id=owner_id).select_related("base_bike"),
                    )
                )
            return qs.filter(is_public=True).prefetch_related(
                Prefetch(
                    "builds",
                    queryset=BikeBuild.objects.filter(
                        is_public=True,
                        base_bike__is_public=True,
                        base_bike__owner_id=owner_id,
                    ).select_related("base_bike"),
                )
            )

        if not self.request.user.is_authenticated:
            return Bike.objects.none()

        qs = Bike.objects.filter(owner=self.request.user)
        if include_hidden:
            return qs.prefetch_related("builds")
        return qs.prefetch_related(
            Prefetch(
                "builds",
                queryset=BikeBuild.objects.filter(
                    is_public=True,
                    base_bike__is_public=True,
                    base_bike__owner=self.request.user,
                ).select_related("base_bike"),
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BikeSerializer

        owner_id = self.request.query_params.get("owner")
        include_hidden = _to_bool(self.request.query_params.get("include_hidden"))

        if owner_id:
            if not self.request.user.is_authenticated:
                return BikePublicListSerializer
            if str(owner_id) != str(self.request.user.id):
                return BikePublicListSerializer
            return BikeSerializer

        if not self.request.user.is_authenticated:
            return BikePublicListSerializer

        return BikeSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=["Bikes"],
        summary="공개 자전거 목록 조회",
        description="특정 사용자의 공개 자전거와 공개 빌드 정보를 반환합니다.",
        parameters=[
            OpenApiParameter(
                name="owner",
                location=OpenApiParameter.QUERY,
                description="자전거 소유자 ID",
                required=True,
                type=str,
            )
        ],
        responses=BikeSerializer(many=True),
    )
    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny], url_path="public")
    def list_public_bikes(self, request):
        owner_id = request.query_params.get("owner")
        if not owner_id:
            return error_response(
                "owner parameter is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MISSING_PARAMETER",
            )

        queryset = Bike.objects.filter(owner_id=owner_id, is_public=True).only(
            "id", "name", "frame_name", "frame_brand", "frame_type", "created_at", "updated_at"
        )
        serializer = BikePublicListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=["Bike Builds"],
        summary="자전거 빌드 목록",
        description="owner 파라미터가 없으면 내 빌드를, 있으면 해당 사용자의 공개 빌드를 반환합니다.",
        parameters=[
            OpenApiParameter(
                name="owner",
                location=OpenApiParameter.QUERY,
                description="소유자 ID. 지정하면 공개 빌드만 조회됩니다.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="include_hidden",
                location=OpenApiParameter.QUERY,
                description="`true`로 지정하면 소유자가 자신의 비공개 빌드까지 조회합니다.",
                required=False,
                type=bool,
            ),
        ],
    ),
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
        queryset = BikeBuild.objects.select_related("base_bike")
        owner_id = self.request.query_params.get("owner")
        include_hidden = _to_bool(self.request.query_params.get("include_hidden"))

        if self.action == "retrieve":
            filters = Q(is_public=True, base_bike__is_public=True)
            if self.request.user.is_authenticated:
                filters |= Q(base_bike__owner=self.request.user)
            return queryset.filter(filters)

        if owner_id:
            queryset = queryset.filter(base_bike__owner_id=owner_id)
            if (
                include_hidden
                and self.request.user.is_authenticated
                and str(self.request.user.id) == str(owner_id)
            ):
                return queryset
            return queryset.filter(is_public=True, base_bike__is_public=True)

        if not self.request.user.is_authenticated:
            return queryset.none()

        if include_hidden or owner_id is None:
            return queryset.filter(base_bike__owner=self.request.user)

        return queryset.filter(
            base_bike__owner=self.request.user,
            is_public=True,
            base_bike__is_public=True,
        )

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
