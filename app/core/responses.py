"""공통 응답 포맷 헬퍼."""
from __future__ import annotations

from typing import Optional

from rest_framework import status
from rest_framework.response import Response


def error_response(
    message: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error: str = "Invalid request",
    code: Optional[str] = None,
) -> Response:
    """문서에 정의된 에러 응답 포맷을 반환합니다."""

    payload = {
        "error": error,
        "message": message,
        "code": code or "INVALID_REQUEST",
    }
    return Response(payload, status=status_code)
