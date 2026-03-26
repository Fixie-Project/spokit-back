"""게시글 관련 모델의 관리자 설정."""
from django.contrib import admin

from .models import Comment, Like, Post, PostImage, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0
    fields = ("purpose", "order", "url", "caption")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("main_title", "status", "frame_brand", "frame_type", "published_at", "author", "view_count")
    list_filter = ("status", "frame_brand", "frame_type", "published_at")
    search_fields = ("main_title", "frame_brand", "frame_type")
    prepopulated_fields = {"slug": ("main_title",)}
    ordering = ("-published_at", "-updated_at")
    autocomplete_fields = ("tags", "author", "submission", "bike", "build", "rider")
    readonly_fields = ("published_at", "view_count", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    inlines = [PostImageInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "user__username", "post__main_title")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    search_fields = ("user__username", "post__main_title")
