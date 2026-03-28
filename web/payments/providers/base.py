from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True)
class PaymentCreateResult:
    payment_id: str
    pay_url: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentWebhookResult:
    event_id: str
    payment_id: str
    status: str
    amount: Decimal | None = None
    amount_minor: int | None = None
    currency: str | None = None
    provider_payload: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(ABC):
    @abstractmethod
    def create_payment(self, order: Mapping[str, Any]) -> PaymentCreateResult:
        """
        Create a remote payment and return provider payment id + checkout URL.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request: Any) -> PaymentWebhookResult:
        """
        Verify provider webhook authenticity and normalize its payload.
        The request object is expected to be Django HttpRequest.
        """
        raise NotImplementedError
