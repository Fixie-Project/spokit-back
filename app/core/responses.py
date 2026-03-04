"""공통 응답 포맷 헬퍼."""
from __future__ import annotations

from typing import Any, Optional

from rest_framework import status
from rest_framework.response import Response


def error_response(
    message: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error: str = "Invalid request",
    code: Optional[str] = None,
    data: Any | None = None,
) -> Response:
    """문서에 정의된 에러 응답 포맷을 반환합니다."""

    payload = {
        "error": error,
        "message": message,
        "code": code or "INVALID_REQUEST",
    }
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)


def success_response(
    message: str,
    data: Any | None = None,
    *,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """통일된 성공 응답 포맷을 반환합니다."""

    payload = {"message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)
