from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from ..config import settings


async def create_plan_order_checkout_session(
    *,
    payment_provider: str,
    order_code: str,
    amount: float,
    currency: str,
) -> dict:
    """Return a provider-agnostic checkout session payload.

    This is scaffolding only. Real provider integrations will return concrete
    gateway identifiers and checkout URLs.
    """
    _ = (payment_provider, order_code, amount, currency)
    return {
        "gateway_status": "not_configured",
        "checkout_url": None,
        "gateway_session_id": None,
        "gateway_order_id": None,
        "message": "Payment gateway integration is pending for this environment.",
    }


def resolve_gateway_status(*, checkout_payload: Optional[dict]) -> str:
    if not checkout_payload:
        return "not_configured"
    status = checkout_payload.get("gateway_status")
    return status if isinstance(status, str) and status else "not_configured"


def verify_payment_webhook_signature(*, provider: str, payload: bytes, signature: Optional[str]) -> tuple[bool, str]:
    provider_key = (provider or "").strip().lower()
    if provider_key not in {"razorpay", "stripe", "payu"}:
        return False, "unsupported_provider"

    secret_map = {
        "razorpay": settings.razorpay_webhook_secret,
        "stripe": settings.stripe_webhook_secret,
        "payu": settings.payu_webhook_secret,
    }
    secret = secret_map.get(provider_key)
    if not secret:
        return False, "webhook_secret_not_configured"

    if not signature:
        return False, "missing_signature"

    signature_value = signature.strip()
    if provider_key == "stripe" and "," in signature_value:
        # Stripe commonly sends "t=...,v1=..."; this scaffold validates v1 only.
        parts = [part.strip() for part in signature_value.split(",")]
        v1_part = next((part for part in parts if part.startswith("v1=")), "")
        signature_value = v1_part.split("=", 1)[1].strip() if "=" in v1_part else ""
        if not signature_value:
            return False, "invalid_signature_format"

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_value):
        return False, "invalid_signature"

    return True, "verified"


def build_webhook_idempotency_key(*, provider: str, event_id: str, payload: bytes) -> str:
    raw = "|".join([(provider or "unknown").strip().lower(), event_id.strip(), hashlib.sha256(payload).hexdigest()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extract_webhook_event_details(*, provider: str, payload: dict) -> dict:
    provider_key = (provider or "").strip().lower()
    data = payload if isinstance(payload, dict) else {}

    event_id = str(data.get("id") or data.get("event_id") or "").strip()
    event_type = str(data.get("event") or data.get("type") or data.get("status") or "unknown").strip()

    gateway_order_id = ""
    gateway_payment_id = ""
    payment_reference = ""
    order_code = ""

    if provider_key == "razorpay":
        event_id = event_id or str(data.get("payload", {}).get("payment", {}).get("entity", {}).get("id") or "").strip()
        gateway_order_id = str(data.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id") or "").strip()
        gateway_payment_id = str(data.get("payload", {}).get("payment", {}).get("entity", {}).get("id") or "").strip()
        payment_reference = gateway_payment_id
        order_code = str(
            data.get("payload", {})
            .get("payment", {})
            .get("entity", {})
            .get("notes", {})
            .get("order_code")
            or ""
        ).strip()
    elif provider_key == "stripe":
        obj = data.get("data", {}).get("object", {})
        event_id = event_id or str(obj.get("id") or "").strip()
        gateway_order_id = str(obj.get("metadata", {}).get("gateway_order_id") or "").strip()
        gateway_payment_id = str(obj.get("id") or "").strip()
        payment_reference = gateway_payment_id
        order_code = str(obj.get("metadata", {}).get("order_code") or "").strip()
    elif provider_key == "payu":
        txnid = str(data.get("txnid") or data.get("transaction_id") or "").strip()
        event_id = event_id or txnid
        gateway_order_id = str(data.get("mihpayid") or data.get("gateway_order_id") or "").strip()
        gateway_payment_id = txnid
        payment_reference = txnid
        order_code = str(data.get("udf1") or data.get("order_code") or "").strip()

    if not event_id:
        event_id = hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    return {
        "provider": provider_key,
        "event_id": event_id,
        "event_type": event_type,
        "gateway_order_id": gateway_order_id or None,
        "gateway_payment_id": gateway_payment_id or None,
        "payment_reference": payment_reference or None,
        "order_code": order_code or None,
    }


def is_payment_success_event(*, provider: str, event_type: str) -> bool:
    provider_key = (provider or "").strip().lower()
    event_value = (event_type or "").strip().lower()
    if provider_key == "razorpay":
        return event_value in {"payment.captured", "order.paid"}
    if provider_key == "stripe":
        return event_value in {"payment_intent.succeeded", "checkout.session.completed", "charge.succeeded"}
    if provider_key == "payu":
        return event_value in {"success", "payment_success", "captured"}
    return False


def is_payment_failure_event(*, provider: str, event_type: str) -> bool:
    provider_key = (provider or "").strip().lower()
    event_value = (event_type or "").strip().lower()
    if provider_key == "razorpay":
        return event_value in {"payment.failed", "order.failed"}
    if provider_key == "stripe":
        return event_value in {"payment_intent.payment_failed", "charge.failed"}
    if provider_key == "payu":
        return event_value in {"failure", "failed", "payment_failed"}
    return False


def is_payment_refund_event(*, provider: str, event_type: str) -> bool:
    provider_key = (provider or "").strip().lower()
    event_value = (event_type or "").strip().lower()
    if provider_key == "razorpay":
        return event_value in {"refund.processed", "payment.refunded"}
    if provider_key == "stripe":
        return event_value in {"charge.refunded", "refund.updated"}
    if provider_key == "payu":
        return event_value in {"refund", "refunded", "payment_refunded"}
    return False
