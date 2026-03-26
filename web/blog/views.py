from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Post


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "blog/home.html")


def index(request: HttpRequest) -> HttpResponse:
    posts = Post.objects.filter(is_published=True, published_at__lte=timezone.now())
    return render(request, "blog/index.html", {"posts": posts})


def post_detail(request: HttpRequest, slug: str) -> HttpResponse:
    post = get_object_or_404(Post, slug=slug, is_published=True, published_at__lte=timezone.now())
    return render(request, "blog/post_detail.html", {"post": post})
