"""소개 신청 관련 관리자 설정입니다."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "submitter_name",
        "submitter_email",
        "status",
        "bike_display",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("submitter_name", "submitter_email", "bike__name", "bike__nickname")
    readonly_fields = ("created_at", "reviewed_at", "bike_preview")
    autocomplete_fields = ("user", "reviewer", "result_post", "bike")
    list_select_related = ("user", "reviewer", "result_post", "bike")

    fieldsets = (
        ("신청자 정보", {"fields": ("user", "submitter_name", "submitter_email", "sns_links", "message")} ),
        ("진행 정보", {"fields": ("status", "notes", "rejection_reason", "reviewer", "reviewed_at", "result_post", "created_at")} ),
        ("바이크", {"fields": ("bike", "bike_preview")} ),
    )

    def bike_display(self, obj: Submission) -> str:
        if not obj.bike:
            return "-"
        return obj.bike.nickname or obj.bike.name

    bike_display.short_description = "바이크"

    def bike_preview(self, obj: Submission) -> str:
        bike = obj.bike
        if not bike:
            return "-"
        spec = getattr(bike, "spec", None)
        parts = "<br />".join(
            f"<strong>{label}</strong>: {value}" for label, value in (spec.display_items if spec else [])
        )
        desc = bike.description.replace("\n", "<br />") if bike.description else ""
        return format_html(
            "<p><strong>{}</strong>{}</p><p>{}</p><p>{}</p>",
            bike.name,
            f" ({bike.nickname})" if bike.nickname else "",
            desc,
            parts or "등록된 부품 정보가 없습니다.",
        )

    bike_preview.short_description = "바이크 상세"
