from django.db import models
from django.utils import timezone


class Post(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, max_length=220)
    summary = models.CharField(max_length=280, blank=True)
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self) -> str:
        return self.title
