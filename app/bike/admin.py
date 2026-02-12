"""바이크 관련 관리자 설정."""
from django.contrib import admin

from .models import Bike, BikeBuild, BikeBuildLike


class BikeBuildInline(admin.TabularInline):
    model = BikeBuild
    extra = 0
    fields = ("title", "components", "note")


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("frame_name", "owner", "is_posted", "updated_at")
    list_filter = ("is_posted",)
    search_fields = ("frame_name", "owner__email", "owner__username")
    inlines = [BikeBuildInline]



@admin.register(BikeBuild)
class BikeBuildAdmin(admin.ModelAdmin):
    list_display = ("base_bike", "title", "updated_at")
    search_fields = ("base_bike__frame_name", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BikeBuildLike)
class BikeBuildLikeAdmin(admin.ModelAdmin):
    list_display = ("build", "user", "created_at")
    search_fields = ("build__title", "user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")
