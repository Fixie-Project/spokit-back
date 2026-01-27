"""Bike and bike build related API views."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import permissions, status
from app.core.pagination import BuildLimitOffsetPagination
from rest_framework.exceptions import PermissionDenied, NotAuthenticated, ValidationError
from rest_framework.views import APIView

from .models import Bike, BikeBuild
from .serializers import (
    BikeBuildDetailResponseSerializer,
    BikeBuildDetailSerializer,
    BikeBuildListResponseSerializer,
    BikeBuildSerializer,
    BikeBuildWriteSerializer,
    BikeDetailResponseSerializer,
    BikeListResponseSerializer,
    BikeSerializer,
    MessageSerializer,
)
from app.core.responses import success_response

PUBLIC_TAG = "Public"


def _bike_examples():
    return [
        OpenApiExample(
            "Bike detail",
            value={
                "message": "자전거를 조회했습니다.",
                "data": {
                    "id": "uuid",
                    "owner": "uuid",
                    "name": "Midnight Stealth",
                    "frame_name": "State 4130 Chromoly",
                    "main_image": {"url": "https://.../main.jpg", "width": 1200, "height": 800},
                    "main_image_url": "https://.../main.jpg",
                    "is_posted": False,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-02T12:00:00Z",
                    "builds": [
                        {
                            "id": "build-uuid",
                            "base_bike": {"id": "uuid", "frame_name": "State 4130 Chromoly"},
                            "title": "Chrome Dreams",
                            "is_public": True,
                            "created_at": "2025-01-02T12:00:00Z",
                            "updated_at": "2025-01-02T12:00:00Z",
                            "main_image": None,
                            "main_image_url": None,
                        }
                    ],
                },
            },
            response_only=True,
        )
    ]


def _build_examples():
    return [
        OpenApiExample(
            "Bike build detail",
            value={
                "message": "자전거 빌드를 조회했습니다.",
                "data": {
                    "id": "build-uuid",
                    "base_bike": {"id": "bike-uuid", "frame_name": "Cinelli Mash Histogram"},
                    "title": "Chrome Dreams",
                    "components": {
                        "frame_setup": ["Cinelli Mash Histogram"],
                        "wheel": ["H+Son Archetype"],
                        "cockpit": ["Nitto B123"],
                    },
                    "note": "",
                    "is_public": True,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-02T12:00:00Z",
                    "main_image": None,
                    "images": [],
                },
            },
            response_only=True,
        )
    ]


def _get_visibility(request, *, default: str | None = None) -> str | None:
    raw = request.query_params.get("visibility")
    if raw:
        value = raw.lower()
        if value not in {"public", "private"}:
            raise ValidationError({"visibility": "허용 값은 public, private 입니다."})
        return value
    return default


class BikeListCreateView(APIView):
    """로그인 사용자의 자전거 목록 조회 및 등록."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Bikes"],
        summary="내 자전거 목록",
        responses=BikeListResponseSerializer,
        examples=_bike_examples(),
    )
    def get(self, request):
        queryset = Bike.objects.filter(owner=request.user).prefetch_related("builds")
        serializer = BikeSerializer(queryset, many=True, context={"request": request})
        return success_response("자전거 목록을 조회했습니다.", serializer.data)

    @extend_schema(tags=["Bikes"], summary="자전거 등록", responses=BikeDetailResponseSerializer)
    def post(self, request):
        serializer = BikeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return success_response(
            "자전거가 등록되었습니다.", serializer.data, status_code=status.HTTP_201_CREATED
        )


class BikeDetailView(APIView):
    """자전거 상세 조회/수정/삭제."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_object(self, bike_id: str) -> Bike:
        return get_object_or_404(Bike.objects.prefetch_related("builds"), pk=bike_id)

    @extend_schema(tags=["Bikes"], summary="자전거 상세 조회", responses=BikeDetailResponseSerializer)
    def get(self, request, bike_id: str):
        bike = self._get_object(bike_id)
        if bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거만 조회할 수 있습니다.")
        serializer = BikeSerializer(bike, context={"request": request})
        return success_response("자전거를 조회했습니다.", serializer.data)

    @extend_schema(tags=["Bikes"], summary="자전거 부분 수정", responses=BikeDetailResponseSerializer)
    def patch(self, request, bike_id: str):
        if not request.user.is_authenticated:
            raise NotAuthenticated("로그인이 필요합니다.")
        bike = self._get_object(bike_id)
        if bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거만 수정할 수 있습니다.")
        serializer = BikeSerializer(
            bike,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("자전거가 수정되었습니다.", serializer.data)

    @extend_schema(tags=["Bikes"], summary="자전거 삭제", responses=MessageSerializer)
    def delete(self, request, bike_id: str):
        if not request.user.is_authenticated:
            raise NotAuthenticated("로그인이 필요합니다.")
        bike = self._get_object(bike_id)
        if bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거만 삭제할 수 있습니다.")
        bike.delete()
        return success_response("자전거가 삭제되었습니다.")


class BikeBuildListCreateView(APIView):
    """로그인 사용자의 빌드 목록 및 등록."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Bike Builds"],
        summary="내 자전거 빌드 목록",
        parameters=[
            OpenApiParameter(
                name="visibility",
                location=OpenApiParameter.QUERY,
                description="`public` 또는 `private` 중 선택. 생략 시 전체",
                required=False,
                type=str,
            )
        ],
        responses=BikeBuildListResponseSerializer,
        examples=_build_examples(),
    )
    def get(self, request):
        visibility = _get_visibility(request, default=None)
        queryset = BikeBuild.objects.filter(base_bike__owner=request.user).select_related("base_bike", "main_image")

        if visibility == "public":
            queryset = queryset.filter(is_public=True)
        elif visibility == "private":
            queryset = queryset.filter(is_public=False)

        ordering = request.query_params.get("ordering", "-created_at")
        allowed_ordering = {"created_at", "-created_at", "title", "-title"}
        if ordering not in allowed_ordering:
            ordering = "-created_at"
        queryset = queryset.order_by(ordering)
        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return success_response("자전거 빌드 목록을 조회했습니다.", serializer.data)

    @extend_schema(
        tags=["Bike Builds"],
        summary="자전거 빌드 등록",
        responses=BikeBuildDetailResponseSerializer,
        examples=_build_examples(),
    )
    def post(self, request):
        serializer = BikeBuildWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        base_bike = serializer.validated_data["base_bike"]
        if base_bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거에만 빌드를 추가할 수 있습니다.")
        build = serializer.save()
        return success_response(
            "자전거 빌드가 등록되었습니다.",
            BikeBuildDetailSerializer(build, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class BikeBuildDetailView(APIView):
    """자전거 빌드 상세/수정/삭제."""

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def _get_object(self, build_id: str) -> BikeBuild:
        return get_object_or_404(
            BikeBuild.objects.select_related("base_bike", "main_image").prefetch_related("images__image"),
            pk=build_id,
        )

    @extend_schema(
        tags=["Bike Builds", PUBLIC_TAG],
        summary="자전거 빌드 상세 조회",
        responses=BikeBuildDetailResponseSerializer,
        examples=_build_examples(),
    )
    def get(self, request, build_id: str):
        build = self._get_object(build_id)
        is_owner = request.user.is_authenticated and build.base_bike.owner_id == request.user.id
        is_public = build.is_public
        if is_owner or is_public:
            serializer = BikeBuildDetailSerializer(build, context={"request": request})
            return success_response("자전거 빌드를 조회했습니다.", serializer.data)
        raise PermissionDenied("이 빌드를 볼 수 있는 권한이 없습니다.")

    @extend_schema(
        tags=["Bike Builds"],
        summary="자전거 빌드 부분 수정",
        responses=BikeBuildDetailResponseSerializer,
        examples=_build_examples(),
    )
    def patch(self, request, build_id: str):
        if not request.user.is_authenticated:
            raise NotAuthenticated("로그인이 필요합니다.")
        build = self._get_object(build_id)
        if build.base_bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거 빌드만 수정할 수 있습니다.")
        serializer = BikeBuildWriteSerializer(
            build,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            "자전거 빌드가 수정되었습니다.",
            BikeBuildDetailSerializer(build, context={"request": request}).data,
        )

    @extend_schema(tags=["Bike Builds"], summary="자전거 빌드 삭제", responses=MessageSerializer)
    def delete(self, request, build_id: str):
        if not request.user.is_authenticated:
            raise NotAuthenticated("로그인이 필요합니다.")
        build = self._get_object(build_id)
        if build.base_bike.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거 빌드만 삭제할 수 있습니다.")
        build.delete()
        return success_response("자전거 빌드가 삭제되었습니다.")


class MyBikeBuildDetailView(BikeBuildDetailView):
    """내 자전거 빌드 상세/수정/삭제."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Bike Builds"],
        summary="내 자전거 빌드 상세 조회",
        responses=BikeBuildDetailResponseSerializer,
        examples=_build_examples(),
    )
    def get(self, request, build_id: str):
        build = self._get_object(build_id)
        if build.base_bike.owner_id != request.user.id:
            raise PermissionDenied("본인 빌드만 조회할 수 있습니다.")
        serializer = BikeBuildDetailSerializer(build, context={"request": request})
        return success_response("자전거 빌드를 조회했습니다.", serializer.data)


class BikeBuildArchiveListView(APIView):
    """전체 공개 빌드 목록."""

    permission_classes = [permissions.AllowAny]
    pagination_class = BuildLimitOffsetPagination

    @extend_schema(
        tags=["Bike Builds", PUBLIC_TAG],
        summary="전체 공개 빌드 목록",
        responses=BikeBuildListResponseSerializer,
        examples=_build_examples(),
    )
    def get(self, request):
        queryset = (
            BikeBuild.objects.filter(is_public=True)
            .select_related("base_bike", "main_image")
            .order_by("-created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = BikeBuildSerializer(page, many=True, context={"request": request})
            payload = {
                "count": paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            }
            return success_response("공개 빌드 목록을 조회했습니다.", payload)
        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return success_response("공개 빌드 목록을 조회했습니다.", serializer.data)
