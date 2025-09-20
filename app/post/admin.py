"""게시글 관련 모델의 관리자 설정입니다."""
from django.contrib import admin

from .models import Comment, Like, Post, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "published_at", "updated_at", "author")
    list_filter = ("status", "featured", "published_at", "tags")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at",)
    autocomplete_fields = ("tags", "author")
    filter_horizontal = ("tags",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at", "is_blocked")
    list_filter = ("is_blocked", "created_at")
    search_fields = ("content", "user__username", "post__title")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    search_fields = ("user__username", "post__title")

