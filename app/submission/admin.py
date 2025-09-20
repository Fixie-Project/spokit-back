"""소개 신청 관련 관리자 설정입니다."""
from django.contrib import admin

from .models import Submission, SubmissionBuildDetail


class SubmissionBuildDetailInline(admin.StackedInline):
    model = SubmissionBuildDetail
    can_delete = False
    extra = 0
    verbose_name = "부품 정보"
    verbose_name_plural = "부품 정보"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "submitter_name",
        "submitter_email",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("submitter_name", "submitter_email")
    readonly_fields = ("created_at", "reviewed_at")
    autocomplete_fields = ("user", "reviewer", "result_post")
    inlines = [SubmissionBuildDetailInline]
