from django.contrib import admin

from .models import (
    BotOrder,
    BotSubscription,
    BotUser,
    LinkedAccount,
    PaymentEvent,
    TelegramLinkToken,
    WebLoginToken,
)


@admin.register(LinkedAccount)
class LinkedAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "created_at")
    search_fields = ("user__username", "telegram_id")


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "consumed_at", "consumed_telegram_id")
    search_fields = ("user__username", "code", "consumed_telegram_id")
    list_filter = ("consumed_at",)


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("id", "client_code", "telegram_id", "username", "first_name", "created_at")
    search_fields = ("client_code", "telegram_id", "username", "first_name")
    ordering = ("-id",)
    list_per_page = 50


@admin.register(BotSubscription)
class BotSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "display_name",
        "inbound_id",
        "client_email",
        "is_active",
        "expires_at",
        "revoked_at",
        "updated_at",
    )
    search_fields = (
        "id",
        "user__client_code",
        "user__telegram_id",
        "display_name",
        "client_email",
        "client_uuid",
    )
    list_filter = ("is_active", "inbound_id")
    ordering = ("-id",)
    list_per_page = 50
    actions = ("mark_inactive", "mark_active")

    @admin.action(description="Отключить выбранные подписки")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Отключено подписок: {updated}")

    @admin.action(description="Активировать выбранные подписки")
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True, revoked_at=None)
        self.message_user(request, f"Активировано подписок: {updated}")


@admin.register(BotOrder)
class BotOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "channel",
        "payment_method",
        "amount_minor",
        "currency_iso",
        "card_provider",
        "card_payment_id",
        "created_at",
        "paid_at",
    )
    search_fields = (
        "id",
        "payload",
        "user__client_code",
        "user__telegram_id",
        "card_payment_id",
        "provider_payment_charge_id",
        "telegram_payment_charge_id",
    )
    list_filter = ("status", "channel", "payment_method", "card_provider")
    ordering = ("-id",)
    list_per_page = 50


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "event_id", "created_at", "processed_at")
    search_fields = ("event_id", "provider")
    list_filter = ("provider",)
    ordering = ("-id",)
    list_per_page = 50


@admin.register(WebLoginToken)
class WebLoginTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "telegram_id", "expires_at", "consumed_at", "created_at")
    search_fields = ("id", "telegram_id", "token")
    list_filter = ("consumed_at",)
    ordering = ("-id",)
    list_per_page = 50
