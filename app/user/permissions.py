"""사용자 역할 기반 권한 클래스."""
from __future__ import annotations

from typing import Iterable

from rest_framework import permissions

from .models import UserRole


class BaseStaffRolePermission(permissions.BasePermission):
    """허용된 운영진 역할을 확인하는 기본 권한 클래스."""

    allowed_roles: Iterable[str] = ()
    message = "필요한 운영진 권한이 없습니다."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        role = getattr(user, "role", None)
        return role in self.allowed_roles


class IsEditorOrAdmin(BaseStaffRolePermission):
    """에디터 또는 관리자 권한 요구."""

    allowed_roles = {UserRole.EDITOR, UserRole.ADMIN}


class IsAdminRole(BaseStaffRolePermission):
    """관리자 권한 요구."""

    allowed_roles = {UserRole.ADMIN}


class IsStaffUser(permissions.BasePermission):
    """임의의 운영진(에디터/관리자) 여부 확인."""

    message = "운영진 계정만 접근할 수 있습니다."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, "role", None) in {UserRole.EDITOR, UserRole.ADMIN}
