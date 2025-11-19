"""Bike and bike build related API views."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, NotAuthenticated, ValidationError
from rest_framework.response import Response
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
    BikePublicListResponseSerializer,
    BikePublicListSerializer,
    BikeSerializer,
    MessageSerializer,
)
from app.core.responses import error_response, success_response


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
        parameters=[
            OpenApiParameter(
                name="visibility",
                location=OpenApiParameter.QUERY,
                description="`public` 또는 `private` 중 선택. 생략 시 전체",
                required=False,
                type=str,
            )
        ],
        responses=BikeListResponseSerializer,
    )
    def get(self, request):
        visibility = _get_visibility(request, default=None)
        queryset = Bike.objects.filter(owner=request.user).prefetch_related("builds")
        if visibility == "public":
            queryset = queryset.filter(is_public=True)
        elif visibility == "private":
            queryset = queryset.filter(is_public=False)
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
        if bike.is_public or bike.owner_id == request.user.id:
            serializer = BikeSerializer(bike, context={"request": request})
            return success_response("자전거를 조회했습니다.", serializer.data)
        raise PermissionDenied("이 자전거를 볼 수 있는 권한이 없습니다.")

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


class BikeOwnerPublicListAPIView(APIView):
    """특정 사용자의 자전거 목록."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Bikes"], summary="사용자 공개 자전거 목록", responses=BikePublicListResponseSerializer)
    def get(self, request, user_id: str):
        if not get_user_model().objects.filter(id=user_id).exists():
            return error_response(
                "사용자를 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        queryset = Bike.objects.filter(owner_id=user_id, is_public=True).prefetch_related(
            Prefetch(
                "builds",
                queryset=BikeBuild.objects.filter(is_public=True).only("id", "title"),
                to_attr="_public_builds",
            )
        ).only(
            "id",
            "name",
            "frame_name",
            "created_at",
            "updated_at",
        )
        serializer = BikePublicListSerializer(queryset, many=True, context={"request": request})
        return success_response("특정 사용자의 자전거 목록을 조회했습니다.", serializer.data)


class BikePublicArchiveListAPIView(APIView):
    """모든 사용자의 공개 자전거 목록."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Bikes"],
        summary="전체 공개 자전거 목록",
        responses=BikePublicListResponseSerializer,
    )
    def get(self, request):
        queryset = Bike.objects.filter(is_public=True).prefetch_related(
            Prefetch(
                "builds",
                queryset=BikeBuild.objects.filter(is_public=True).only("id", "title"),
                to_attr="_public_builds",
            )
        ).only(
            "id",
            "name",
            "frame_name",
            "created_at",
            "updated_at",
        )
        serializer = BikePublicListSerializer(queryset, many=True, context={"request": request})
        return success_response("공개 자전거 목록을 조회했습니다.", serializer.data)


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
    )
    def get(self, request):
        visibility = _get_visibility(request, default=None)
        queryset = BikeBuild.objects.filter(base_bike__owner=request.user).select_related("base_bike")
        if visibility == "public":
            queryset = queryset.filter(is_public=True, base_bike__is_public=True)
        elif visibility == "private":
            queryset = queryset.filter(is_public=False)
        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return success_response("자전거 빌드 목록을 조회했습니다.", serializer.data)

    @extend_schema(tags=["Bike Builds"], summary="자전거 빌드 등록", responses=BikeBuildDetailResponseSerializer)
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
        return get_object_or_404(BikeBuild.objects.select_related("base_bike"), pk=build_id)

    @extend_schema(tags=["Bike Builds"], summary="자전거 빌드 상세 조회", responses=BikeBuildDetailResponseSerializer)
    def get(self, request, build_id: str):
        build = self._get_object(build_id)
        is_owner = request.user.is_authenticated and build.base_bike.owner_id == request.user.id
        is_public = build.is_public and build.base_bike.is_public
        if is_owner or is_public:
            serializer = BikeBuildDetailSerializer(build, context={"request": request})
            return success_response("자전거 빌드를 조회했습니다.", serializer.data)
        raise PermissionDenied("이 빌드를 볼 수 있는 권한이 없습니다.")

    @extend_schema(tags=["Bike Builds"], summary="자전거 빌드 부분 수정", responses=BikeBuildDetailResponseSerializer)
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
        new_base = serializer.validated_data.get("base_bike", build.base_bike)
        if new_base.owner_id != request.user.id:
            raise PermissionDenied("본인 자전거 빌드만 수정할 수 있습니다.")
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


class BikeBuildPublicListView(APIView):
    """특정 사용자의 공개 빌드 목록."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Bike Builds"], summary="사용자 공개 빌드 목록", responses=BikeBuildListResponseSerializer)
    def get(self, request, user_id: str):
        queryset = BikeBuild.objects.filter(
            base_bike__owner_id=user_id,
            is_public=True,
            base_bike__is_public=True,
        ).select_related("base_bike")
        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return success_response("공개 자전거 빌드 목록을 조회했습니다.", serializer.data)


class BikeBuildByBikeListView(APIView):
    """특정 자전거에 연결된 빌드 목록."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Bike Builds"], summary="자전거별 빌드 목록", responses=BikeBuildListResponseSerializer)
    def get(self, request, bike_id: str):
        bike = Bike.objects.filter(pk=bike_id).first()
        if not bike:
            return error_response(
                "자전거를 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
            )

        queryset = bike.builds.select_related("base_bike")
        if bike.owner_id != request.user.id and not request.user.is_staff:
            if not bike.is_public:
                return error_response(
                    "이 자전거의 빌드를 볼 수 있는 권한이 없습니다.",
                    status_code=status.HTTP_403_FORBIDDEN,
                    code="FORBIDDEN",
                )
            queryset = queryset.filter(is_public=True)

        serializer = BikeBuildSerializer(queryset, many=True, context={"request": request})
        return success_response("자전거별 빌드 목록을 조회했습니다.", serializer.data)
