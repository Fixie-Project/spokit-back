"""Submission admin configuration for the new schema."""
import json

from django.contrib import admin
from django.utils.html import format_html

from .models import Submission, SubmissionImage, SubmissionStatusLog


class SubmissionImageInline(admin.TabularInline):
    model = SubmissionImage
    extra = 0
    fields = ("purpose", "order", "url", "caption", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "status",
        "bike",
        "build",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username", "user__email", "bike__frame_name")
    readonly_fields = ("created_at", "updated_at", "story_blocks_pretty", "build_snapshot_pretty")
    autocomplete_fields = ("user", "bike", "build")
    list_select_related = ("user", "bike", "build")
    inlines = (SubmissionImageInline,)

    fieldsets = (
        (
            "기본 정보",
            {
                "fields": (
                    "user",
                    "title",
                    "bike",
                    "build",
                    "status",
                    "reason_code",
                    "reason_detail",
                )
            },
        ),
        (
            "스토리",
            {"fields": ("build_snapshot_pretty", "story_blocks_pretty")},
        ),
        (
            "시스템",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def story_blocks_pretty(self, obj: Submission) -> str:
        if not obj.story_blocks:
            return "-"
        formatted = json.dumps(obj.story_blocks, ensure_ascii=False, indent=2)
        return format_html("<pre style='white-space: pre-wrap;'>{}</pre>", formatted)

    story_blocks_pretty.short_description = "스토리 블록"

    def build_snapshot_pretty(self, obj: Submission) -> str:
        if not obj.build_snapshot:
            return "-"
        formatted = json.dumps(obj.build_snapshot, ensure_ascii=False, indent=2)
        return format_html("<pre style='white-space: pre-wrap;'>{}</pre>", formatted)

    build_snapshot_pretty.short_description = "빌드 스냅샷"


@admin.register(SubmissionStatusLog)
class SubmissionStatusLogAdmin(admin.ModelAdmin):
    list_display = ("submission", "from_status", "to_status", "changed_by_staff", "changed_by_user", "changed_at")
    list_filter = ("to_status", "changed_at")
    search_fields = ("submission__title", "changed_by_staff__user__nickname", "changed_by_user__nickname")
    autocomplete_fields = ("submission", "changed_by_staff", "changed_by_user")
    readonly_fields = ("created_at", "updated_at", "changed_at")
