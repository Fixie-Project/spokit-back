"""관리자 사이트 설정."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Staff, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """커스텀 사용자 모델 관리자."""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("개인 정보"), {"fields": ("username", "nickname", "region", "intro", "sns_link", "profile_image")}),
        (_("권한"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("중요 시각"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "nickname", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )
    list_display = ("email", "nickname", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "nickname", "username")
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """운영진 모델 관리자."""

    list_display = ("user", "role", "contact_email", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "user__nickname", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
