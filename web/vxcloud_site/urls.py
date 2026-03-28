from django.contrib import admin
from django.urls import include, path
from cabinet.views import EmailLoginView, create_magic_link, open_app_link, payment_webhook, telegram_webapp_auth, tg_magic_login
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cms-admin/", include(wagtailadmin_urls)),
    path("cms-documents/", include(wagtaildocs_urls)),
    path("accounts/login/", EmailLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/auth/magic-link", create_magic_link, name="api_magic_link"),
    path("api/auth/telegram/webapp", telegram_webapp_auth, name="api_telegram_webapp_auth"),
    path("api/webhooks/<str:provider>", payment_webhook, name="api_payment_webhook"),
    path("auth/tg/<str:token>", tg_magic_login, name="tg_magic_login"),
    path("account/", include("cabinet.urls")),
    path("open-app/", open_app_link, name="open_app_link"),
    path("legacy/", include("blog.urls")),
    path("", include(wagtail_urls)),
]
