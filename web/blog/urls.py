from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="blog_home"),
    path("instructions/", views.index, name="blog_index"),
    path("post/<slug:slug>/", views.post_detail, name="blog_post_detail"),
]
