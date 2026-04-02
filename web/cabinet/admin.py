from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from .models import (
    BotOrder,
    BotSubscription,
    BotUser,
    LinkedAccount,
    PaymentEvent,
    TelegramLinkToken,
    VPNNode,
    VPNNodeClient,
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


@admin.register(VPNNode)
class VPNNodeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "region",
        "backend_endpoint",
        "is_active",
        "lb_enabled",
        "needs_backfill",
        "last_health_ok",
        "last_health_at",
        "reality_key_fingerprint",
        "last_backfill_at",
    )
    list_filter = ("lb_enabled", "is_active", "needs_backfill", "last_health_ok")
    search_fields = ("name", "region", "backend_host", "xui_base_url", "last_health_error", "last_reality_sni")
    ordering = ("name",)
    list_per_page = 50
    readonly_fields = (
        "backend_endpoint",
        "health_status",
        "reality_key_fingerprint",
        "reality_signature",
        "reality_reference_signature",
        "reality_mismatch_indicator",
        "created_at",
        "updated_at",
    )
    actions = (
        "request_backfill",
        "enable_lb",
        "disable_lb",
        "mark_inactive",
        "mark_active",
    )
    fieldsets = (
        (
            "Identity",
            {
                "fields": ("name", "region", "backend_endpoint"),
            },
        ),
        (
            "Connection",
            {
                "fields": (
                    "xui_base_url",
                    "xui_username",
                    "xui_password",
                    "xui_inbound_id",
                )
            },
        ),
        (
            "Routing",
            {
                "fields": (
                    "backend_host",
                    "backend_port",
                    "backend_weight",
                    "lb_enabled",
                ),
            },
        ),
        (
            "Health",
            {
                "fields": (
                    "health_status",
                    "last_health_ok",
                    "last_health_at",
                    "last_health_error",
                    "reality_key_fingerprint",
                    "reality_signature",
                    "reality_reference_signature",
                    "reality_mismatch_indicator",
                ),
            },
        ),
        (
            "Operations",
            {
                "fields": (
                    "is_active",
                    "needs_backfill",
                    "backfill_requested_at",
                    "last_backfill_at",
                    "last_backfill_error",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @staticmethod
    def _reality_tuple(obj: VPNNode) -> tuple[str, str, str, str] | None:
        values = (
            (obj.last_reality_public_key or "").strip(),
            (obj.last_reality_short_id or "").strip(),
            (obj.last_reality_sni or "").strip(),
            (obj.last_reality_fingerprint or "").strip(),
        )
        if not any(values):
            return None
        return values

    @staticmethod
    def _reference_node(obj: VPNNode) -> VPNNode | None:
        queryset = VPNNode.objects.filter(
            lb_enabled=True,
            is_active=True,
            last_health_ok=True,
        ).exclude(last_reality_public_key__isnull=True).exclude(last_reality_public_key="")
        if obj.pk:
            queryset = queryset.exclude(pk=obj.pk)
        return queryset.order_by("id").first()

    @admin.display(description="Backend")
    def backend_endpoint(self, obj: VPNNode) -> str:
        return f"{obj.backend_host}:{obj.backend_port}"

    @admin.display(description="Health")
    def health_status(self, obj: VPNNode) -> str:
        if obj.last_health_ok is True:
            return "healthy"
        if obj.last_health_ok is False:
            return "unhealthy"
        return "unknown"

    @admin.display(description="REALITY signature")
    def reality_signature(self, obj: VPNNode) -> str:
        current = self._reality_tuple(obj)
        if current is None:
            return "—"
        pub, short_id, sni, fp = current
        short_pub = f"{pub[:16]}..." if len(pub) > 16 else pub
        return f"pbk={short_pub}; sid={short_id or '-'}; sni={sni or '-'}; fp={fp or '-'}"

    @admin.display(description="REALITY key fp")
    def reality_key_fingerprint(self, obj: VPNNode) -> str:
        key = (obj.last_reality_public_key or "").strip()
        if not key:
            return "—"
        return key[-12:] if len(key) > 12 else key

    @admin.display(description="Reference signature")
    def reality_reference_signature(self, obj: VPNNode) -> str:
        reference = self._reference_node(obj)
        if reference is None:
            return "—"
        ref_tuple = self._reality_tuple(reference)
        if ref_tuple is None:
            return "—"
        pub, short_id, sni, fp = ref_tuple
        short_pub = f"{pub[:16]}..." if len(pub) > 16 else pub
        return f"{reference.name}: pbk={short_pub}; sid={short_id or '-'}; sni={sni or '-'}; fp={fp or '-'}"

    @admin.display(description="REALITY mismatch")
    def reality_mismatch_indicator(self, obj: VPNNode) -> str:
        current = self._reality_tuple(obj)
        if current is None:
            return "unknown"
        reference = self._reference_node(obj)
        if reference is None:
            return "n/a"
        ref_tuple = self._reality_tuple(reference)
        if ref_tuple is None:
            return "n/a"
        return "mismatch" if current != ref_tuple else "match"

    @admin.action(description="Request backfill")
    def request_backfill(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(
            needs_backfill=True,
            backfill_requested_at=now,
            last_backfill_error=None,
            updated_at=now,
        )
        self.message_user(request, f"Backfill requested for nodes: {updated}")

    @admin.action(description="Enable LB")
    def enable_lb(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(lb_enabled=True, updated_at=now)
        self.message_user(request, f"LB enabled for nodes: {updated}")

    @admin.action(description="Disable LB")
    def disable_lb(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(lb_enabled=False, updated_at=now)
        self.message_user(request, f"LB disabled for nodes: {updated}")

    @admin.action(description="Mark inactive")
    def mark_inactive(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(is_active=False, lb_enabled=False, updated_at=now)
        self.message_user(request, f"Marked inactive nodes: {updated}")

    @admin.action(description="Mark active")
    def mark_active(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(is_active=True, updated_at=now)
        self.message_user(request, f"Marked active nodes: {updated}")


@admin.register(VPNNodeClient)
class VPNNodeClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "node",
        "subscription_id",
        "sync_state",
        "last_synced_at",
        "last_error",
    )
    list_filter = ("sync_state", "desired_enabled", "observed_enabled")
    search_fields = (
        "node__name",
        "subscription_id",
        "client_email",
        "client_uuid",
        "xui_sub_id",
        "last_error",
    )
    ordering = ("-id",)
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


def ops_dashboard_view(request):
    now = timezone.now()
    day_ago = now - timedelta(days=1)
    week_ahead = now + timedelta(days=7)

    total_users = BotUser.objects.count()
    total_subscriptions = BotSubscription.objects.count()
    active_subscriptions = BotSubscription.objects.filter(
        is_active=True,
        revoked_at__isnull=True,
        expires_at__gt=now,
    ).count()
    expiring_7d = BotSubscription.objects.filter(
        is_active=True,
        revoked_at__isnull=True,
        expires_at__gt=now,
        expires_at__lte=week_ahead,
    ).count()

    total_orders = BotOrder.objects.count()
    pending_orders = BotOrder.objects.filter(status="pending").count()
    paid_24h = BotOrder.objects.filter(
        status__in=["paid", "activating", "activated"],
        paid_at__gte=day_ago,
    ).count()

    webhook_events_24h = PaymentEvent.objects.filter(created_at__gte=day_ago).count()
    unprocessed_webhooks = PaymentEvent.objects.filter(processed_at__isnull=True).count()

    recent_orders = BotOrder.objects.select_related("user").order_by("-id")[:20]
    recent_subscriptions = BotSubscription.objects.select_related("user").order_by("-id")[:20]
    recent_webhooks = PaymentEvent.objects.order_by("-id")[:20]

    top_users = (
        BotUser.objects.annotate(
            total_subs=Count("botsubscription"),
            active_subs=Count(
                "botsubscription",
                filter=Q(
                    botsubscription__is_active=True,
                    botsubscription__revoked_at__isnull=True,
                    botsubscription__expires_at__gt=now,
                ),
            ),
        )
        .order_by("-active_subs", "-total_subs", "id")[:10]
    )

    context = {
        **admin.site.each_context(request),
        "title": "Ops Dashboard",
        "metrics": {
            "total_users": total_users,
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "expiring_7d": expiring_7d,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "paid_24h": paid_24h,
            "webhook_events_24h": webhook_events_24h,
            "unprocessed_webhooks": unprocessed_webhooks,
        },
        "recent_orders": recent_orders,
        "recent_subscriptions": recent_subscriptions,
        "recent_webhooks": recent_webhooks,
        "top_users": top_users,
    }
    return TemplateResponse(request, "admin/ops_dashboard.html", context)


_original_get_urls = admin.site.get_urls


def _get_urls():
    custom_urls = [
        path("ops/", admin.site.admin_view(ops_dashboard_view), name="ops_dashboard"),
    ]
    return custom_urls + _original_get_urls()


admin.site.get_urls = _get_urls
