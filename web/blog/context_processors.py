from blog.models import Page


def navigation_pages(request):
    pages = Page.objects.filter(is_published=True, show_in_nav=True).order_by("nav_order", "title")
    return {"cms_nav_pages": pages}
