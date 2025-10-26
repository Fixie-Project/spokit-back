"""바이크 관련 관리자 설정."""
from django.contrib import admin

from .models import Bike, BikeBuild


class BikeBuildInline(admin.TabularInline):
    model = BikeBuild
    extra = 0
    fields = ("title", "components", "note")


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("frame_name", "owner", "is_public", "is_posted", "updated_at")
    list_filter = ("is_public", "is_posted")
    search_fields = ("frame_name", "owner__email", "owner__nickname")
    inlines = [BikeBuildInline]



@admin.register(BikeBuild)
class BikeBuildAdmin(admin.ModelAdmin):
    list_display = ("base_bike", "title", "updated_at")
    search_fields = ("base_bike__frame_name", "title")
    readonly_fields = ("created_at", "updated_at")
