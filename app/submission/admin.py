"""소개 신청 관련 관리자 설정입니다."""
import json

from django.contrib import admin
from django.utils.html import format_html

from .models import Submission, SubmissionImage


class SubmissionImageInline(admin.TabularInline):
    model = SubmissionImage
    extra = 0
    fields = ("image", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "user_email",
        "title",
        "status",
        "blocks_count",
        "bike_display",
        "image_count",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username", "user__email", "bike__name")
    readonly_fields = ("created_at", "reviewed_at", "bike_preview", "story_blocks_pretty")
    autocomplete_fields = ("user", "reviewer", "result_post", "bike")
    list_select_related = ("user", "reviewer", "result_post", "bike")
    inlines = (SubmissionImageInline,)

    fieldsets = (
        (
            "신청자 정보",
            {
                "fields": (
                    "user",
                    "title",
                    "sns_links",
                    "external_story_url",
                    "required_question_ids",
                    "story_blocks_pretty",
                )
            },
        ),
        (
            "진행 정보",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "reviewer",
                    "reviewed_at",
                    "result_post",
                    "created_at",
                )
            },
        ),
        ("바이크", {"fields": ("bike", "bike_preview")} ),
    )

    def bike_display(self, obj: Submission) -> str:
        if not obj.bike:
            return "-"
        return obj.bike.name

    bike_display.short_description = "바이크"

    def user_email(self, obj: Submission) -> str:
        if not obj.user:
            return "-"
        return obj.user.email or obj.user.get_username()

    user_email.short_description = "이메일"

    def image_count(self, obj: Submission) -> int:
        return obj.images.count()

    image_count.short_description = "이미지 수"

    def story_blocks_pretty(self, obj: Submission) -> str:
        if not obj.story_blocks:
            return "-"
        formatted = json.dumps(obj.story_blocks, ensure_ascii=False, indent=2)
        return format_html("<pre style='white-space: pre-wrap;'>{}</pre>", formatted)

    story_blocks_pretty.short_description = "스토리 블록"

    def bike_preview(self, obj: Submission) -> str:
        bike = obj.bike
        if not bike:
            return "-"
        spec = getattr(bike, "spec", None)
        parts = "<br />".join(
            f"<strong>{label}</strong>: {value}" for label, value in (spec.display_items if spec else [])
        )
        return format_html(
            "<p><strong>{}</strong></p><p>{}</p>",
            bike.name,
            parts or "등록된 부품 정보가 없습니다.",
        )

    bike_preview.short_description = "바이크 상세"
