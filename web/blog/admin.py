from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "summary", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at", "-id")
