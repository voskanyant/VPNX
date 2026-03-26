from django.contrib import admin

from .models import LinkedAccount, TelegramLinkToken


@admin.register(LinkedAccount)
class LinkedAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "created_at")
    search_fields = ("user__username", "telegram_id")


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "consumed_at", "consumed_telegram_id")
    search_fields = ("user__username", "code", "consumed_telegram_id")
    list_filter = ("consumed_at",)
