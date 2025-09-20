"""바이크 관련 관리자 설정입니다."""
from django.contrib import admin

from .models import Bike, BikeSpec


class BikeSpecInline(admin.StackedInline):
    model = BikeSpec
    can_delete = False
    extra = 0


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("owner", "name", "nickname", "is_primary", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("name", "nickname", "owner__username", "owner__email")
    inlines = [BikeSpecInline]
    ordering = ("owner", "-is_primary", "name")


@admin.register(BikeSpec)
class BikeSpecAdmin(admin.ModelAdmin):
    list_display = ("bike", "updated_at")
    search_fields = ("bike__name", "bike__nickname", "bike__owner__username")
    readonly_fields = ("updated_at",)
