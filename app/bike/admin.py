"""바이크 관련 관리자 설정."""
from django.contrib import admin

from .models import Bike, BikeBuild


class BikeBuildInline(admin.TabularInline):
    model = BikeBuild
    extra = 0
    fields = ("title", "components", "note")


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("frame_brand", "frame_name", "owner", "is_public", "is_posted", "updated_at")
    list_filter = ("frame_brand", "frame_type", "is_public", "is_posted")
    search_fields = ("frame_brand", "frame_name", "owner__email", "owner__nickname")
    inlines = [BikeBuildInline]
    ordering = ("frame_brand", "frame_name")


@admin.register(BikeBuild)
class BikeBuildAdmin(admin.ModelAdmin):
    list_display = ("base_bike", "title", "updated_at")
    search_fields = ("base_bike__frame_brand", "base_bike__frame_name", "title")
    list_filter = ("base_bike__frame_brand",)
    readonly_fields = ("created_at", "updated_at")
