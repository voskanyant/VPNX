from django import forms
from django.contrib import admin

from .models import Post


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = "__all__"
        widgets = {
            "content": forms.Textarea(attrs={"class": "js-richtext", "rows": 28}),
        }

    class Media:
        js = (
            "https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js",
            "admin/post_editor.js",
        )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "summary", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at", "-id")
