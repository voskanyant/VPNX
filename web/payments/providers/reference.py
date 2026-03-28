from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from decimal import Decimal
from typing import Any, Mapping
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest

from .base import PaymentCreateResult, PaymentProvider, PaymentWebhookResult


class ReferencePaymentProvider(PaymentProvider):
    """
    Reference (mock) provider used by default.
    It provides stable behavior for integration without binding to a real PSP.
    """

    def __init__(self) -> None:
        try:
            base_url = str(getattr(settings, "PAYMENT_REFERENCE_BASE_URL", "https://pay.vxcloud.ru/mock"))
            webhook_secret = str(getattr(settings, "PAYMENT_REFERENCE_WEBHOOK_SECRET", ""))
        except ImproperlyConfigured:
            base_url = os.getenv("PAYMENT_REFERENCE_BASE_URL", "https://pay.vxcloud.ru/mock")
            webhook_secret = os.getenv("PAYMENT_REFERENCE_WEBHOOK_SECRET", "")

        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret.strip()

    def create_payment(self, order: Mapping[str, Any]) -> PaymentCreateResult:
        order_id = int(order["id"])
        payment_id = f"refpay_{order_id}_{secrets.token_hex(6)}"
        query = urlencode(
            {
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_minor": order.get("amount_minor") or 0,
                "currency": order.get("currency_iso") or "RUB",
            }
        )
        pay_url = f"{self.base_url}/checkout?{query}"
        return PaymentCreateResult(payment_id=payment_id, pay_url=pay_url)

    def verify_webhook(self, request: HttpRequest) -> PaymentWebhookResult:
        raw = request.body or b""
        self._validate_signature(raw, request.headers.get("X-Reference-Signature"))

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Invalid webhook JSON payload") from exc

        event_id = str(payload.get("event_id") or "")
        payment_id = str(payload.get("payment_id") or "")
        status = str(payload.get("status") or "")
        if not event_id or not payment_id or not status:
            raise ValueError("Webhook payload must include event_id, payment_id, status")

        amount_minor_value = payload.get("amount_minor")
        amount_minor = int(amount_minor_value) if amount_minor_value is not None else None
        amount = None
        if amount_minor is not None:
            amount = Decimal(amount_minor) / Decimal(100)

        currency = payload.get("currency_iso")
        currency_iso = str(currency).upper() if currency else None

        return PaymentWebhookResult(
            event_id=event_id,
            payment_id=payment_id,
            status=status,
            amount=amount,
            amount_minor=amount_minor,
            currency=currency_iso,
            provider_payload=payload,
        )

    def _validate_signature(self, raw_body: bytes, signature: str | None) -> None:
        if not self.webhook_secret:
            return
        provided = (signature or "").strip().lower()
        if not provided:
            raise ValueError("Missing webhook signature")

        expected = hmac.new(self.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provided):
            raise ValueError("Invalid webhook signature")
