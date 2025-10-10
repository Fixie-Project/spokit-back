from django.contrib import admin

from .models import SubmissionReviewNote


@admin.register(SubmissionReviewNote)
class SubmissionReviewNoteAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "author",
        "post",
        "post_status",
        "created_at",
        "updated_at",
    )
    list_filter = ("post_status", "created_at")
    search_fields = (
        "submission__title",
        "submission__user__username",
        "author__username",
        "note",
    )
    autocomplete_fields = ("submission", "author", "post")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("submission", "author", "post", "post_status", "note")}),
        ("기록", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
