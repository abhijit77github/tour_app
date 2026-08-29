from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from ..config import settings
from .payment_provider import is_payment_failure_event, is_payment_refund_event, is_payment_success_event


PLANNER_BILLING_SETTINGS_KEY = "planner_billing"
PLAN_ORDER_OPEN_STATUSES = {
    "pending_payment",
    "payment_pending",
    "payment_received",
    "fulfillment_pending",
}
PLAN_ORDER_TERMINAL_STATUSES = {"completed", "cancelled", "expired", "failed"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def billing_cycle_window(reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    start = reference or utc_now()
    end = start + timedelta(days=30)
    return start, end


def build_plan_order_code() -> str:
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    return f"PORD-{stamp}-{uuid4().hex[:8].upper()}"


def build_plan_snapshot(plan_doc: dict) -> dict:
    return {
        "code": plan_doc["code"],
        "name": plan_doc.get("name", plan_doc["code"]),
        "description": plan_doc.get("description", ""),
        "monthly_price": float(plan_doc.get("monthly_price") or 0),
        "currency": plan_doc.get("currency", "INR"),
        "included_credits": int(plan_doc.get("included_credits") or 0),
        "features": list(plan_doc.get("features") or []),
    }


def build_plan_order_history_entry(
    *,
    order_status: str,
    payment_status: str,
    fulfillment_status: str,
    actor_id: Optional[str],
    note: str,
    metadata: Optional[dict] = None,
) -> dict:
    return {
        "timestamp": utc_now(),
        "order_status": order_status,
        "payment_status": payment_status,
        "fulfillment_status": fulfillment_status,
        "actor_id": actor_id,
        "note": note,
        "metadata": metadata or {},
    }


def build_plan_assignment_note(order_code: str, plan_name: str, settlement_notes: Optional[str]) -> str:
    base_note = f"Plan order {order_code} activated {plan_name}"
    if settlement_notes:
        return f"{base_note}. {settlement_notes}"
    return base_note


def build_click_idempotency_key(
    *,
    promotion_id: str,
    source: str,
    session_id: Optional[str],
    request_id: Optional[str],
    client_host: Optional[str],
    user_agent: Optional[str],
    current_time: Optional[datetime] = None,
) -> str:
    dedupe_minutes = max(1, min(int(settings.billing_search_click_dedupe_minutes or 30), 24 * 60))
    identity_mode = str(settings.billing_search_click_identity_mode or "session_first").strip().lower()

    now = current_time or utc_now()
    bucket_minutes = (now.hour * 60 + now.minute) // dedupe_minutes

    fallback_fingerprint = "|".join([
        client_host or "unknown-host",
        (user_agent or "unknown-agent")[:120],
    ])
    if identity_mode == "request_first":
        fingerprint = request_id or session_id or fallback_fingerprint
    elif identity_mode == "fingerprint_only":
        fingerprint = fallback_fingerprint
    else:
        fingerprint = session_id or request_id or fallback_fingerprint

    raw = "|".join([
        promotion_id,
        source,
        fingerprint,
        now.strftime("%Y-%m-%d"),
        str(bucket_minutes),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_planner_impression_source_reference(
    *,
    session_id: str,
    operator_profile_id: str,
    request_key: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> str:
    scope = str(settings.billing_planner_impression_scope or "session").strip().lower()
    now = current_time or utc_now()

    if scope == "request":
        return f"{session_id}:{operator_profile_id}:impression:{request_key or now.strftime('%Y%m%d%H%M%S%f')}"
    if scope == "daily":
        return f"{session_id}:{operator_profile_id}:impression:{now.strftime('%Y%m%d')}"
    return f"{session_id}:{operator_profile_id}:impression"


def should_auto_apply_refund_compensation() -> bool:
    mode = str(settings.billing_refund_compensation_mode or "manual").strip().lower()
    return mode in {"automatic", "auto"}


def build_request_fingerprint(
    *,
    session_id: Optional[str],
    request_id: Optional[str],
    client_host: Optional[str],
    user_agent: Optional[str],
) -> str:
    raw = "|".join([
        session_id or "",
        request_id or "",
        client_host or "",
        (user_agent or "")[:120],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_billing_event_idempotency_key(
    *,
    source_surface: str,
    event_type: str,
    operator_profile_id: str,
    source_reference_type: str,
    source_reference_id: Optional[str],
    anonymous_session_id: Optional[str] = None,
) -> str:
    raw = "|".join(
        [
            source_surface,
            event_type,
            operator_profile_id,
            source_reference_type,
            source_reference_id or "",
            anonymous_session_id or "",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def append_billing_event(
    db,
    *,
    operator_profile_id: str,
    source_surface: str,
    event_type: str,
    source_reference_type: str,
    source_reference_id: Optional[str],
    anonymous_session_id: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
    outcome_reason: Optional[str] = None,
    metadata: Optional[dict] = None,
    promotion_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> bool:
    event_idempotency_key = idempotency_key or build_billing_event_idempotency_key(
        source_surface=source_surface,
        event_type=event_type,
        operator_profile_id=operator_profile_id,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        anonymous_session_id=anonymous_session_id,
    )

    document = {
        "idempotency_key": event_idempotency_key,
        "operator_profile_id": operator_profile_id,
        "promotion_id": promotion_id,
        "source_surface": source_surface,
        "event_type": event_type,
        "source_reference_type": source_reference_type,
        "source_reference_id": source_reference_id,
        "anonymous_session_id": anonymous_session_id,
        "request_fingerprint": request_fingerprint,
        "credits_charged": 0,
        "currency_amount": 0,
        "is_billable": False,
        "outcome_reason": outcome_reason,
        "metadata": metadata or {},
        "created_at": utc_now(),
    }

    result = await db.billing_event_log.update_one(
        {"idempotency_key": event_idempotency_key},
        {"$setOnInsert": document},
        upsert=True,
    )
    return bool(result.upserted_id)


def get_default_planner_pricing_summary() -> dict:
    return {
        "search_profile_click": settings.search_profile_click_credits,
        "planner_intent_click": settings.planner_intent_click_credits,
        "qualified_lead": settings.planner_qualified_lead_credits,
        "conversion": settings.planner_conversion_credits,
    }


def _normalize_planner_credit_value(value: object) -> int:
    try:
        return max(min(int(value or 0), 100), 0)
    except (TypeError, ValueError):
        return 0


async def get_planner_pricing_summary(db=None) -> dict:
    pricing = {
        key: _normalize_planner_credit_value(value)
        for key, value in get_default_planner_pricing_summary().items()
    }

    if db is None or not hasattr(db, "admin_settings"):
        return pricing

    persisted = await db.admin_settings.find_one({"key": PLANNER_BILLING_SETTINGS_KEY})
    persisted_value = (persisted or {}).get("value")
    if isinstance(persisted_value, dict):
        legacy_intent_value = persisted_value.get("planner_intent_click")
        if legacy_intent_value is None and "qualified_lead" in persisted_value:
            legacy_intent_value = persisted_value.get("qualified_lead")
        for key in pricing:
            if key == "planner_intent_click" and legacy_intent_value is not None:
                pricing[key] = _normalize_planner_credit_value(legacy_intent_value)
            elif key in persisted_value:
                pricing[key] = _normalize_planner_credit_value(persisted_value.get(key))
    return pricing


async def get_planner_pricing_settings_document(db=None) -> dict:
    pricing = await get_planner_pricing_summary(db)
    if db is None or not hasattr(db, "admin_settings"):
        return {
            "values": pricing,
            "source": "environment",
            "updated_at": None,
            "updated_by": None,
        }

    persisted = await db.admin_settings.find_one({"key": PLANNER_BILLING_SETTINGS_KEY})
    if not persisted:
        return {
            "values": pricing,
            "source": "environment",
            "updated_at": None,
            "updated_by": None,
        }

    return {
        "values": pricing,
        "source": "database",
        "updated_at": persisted.get("updated_at"),
        "updated_by": persisted.get("updated_by"),
    }


async def get_planner_event_credit_value(db, event_type: str) -> int:
    pricing = await get_planner_pricing_summary(db)
    return pricing.get(event_type, 0)


def _billing_pricing_lookup_key(*, source_surface: str, event_type: str) -> Optional[str]:
    if source_surface == "search" and event_type == "profile_click":
        return "search_profile_click"
    if source_surface == "planner" and event_type == "intent_click":
        return "planner_intent_click"
    if source_surface == "planner" and event_type == "qualified_lead":
        return "qualified_lead"
    if source_surface == "planner" and event_type == "conversion":
        return "conversion"
    return None


async def get_billing_event_credit_value(db, *, source_surface: str, event_type: str) -> int:
    lookup_key = _billing_pricing_lookup_key(source_surface=source_surface, event_type=event_type)
    if not lookup_key:
        return 0
    pricing = await get_planner_pricing_summary(db)
    return pricing.get(lookup_key, 0)


async def append_configurable_billing_event(
    db,
    *,
    operator_profile_id: str,
    source_surface: str,
    event_type: str,
    source_reference_type: str,
    source_reference_id: Optional[str],
    anonymous_session_id: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
    outcome_reason: Optional[str] = None,
    metadata: Optional[dict] = None,
    promotion_id: Optional[str] = None,
    currency_amount_on_success: float = 0,
    notes: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    configured_credits = await get_billing_event_credit_value(
        db,
        source_surface=source_surface,
        event_type=event_type,
    )
    event_idempotency_key = idempotency_key or build_billing_event_idempotency_key(
        source_surface=source_surface,
        event_type=event_type,
        operator_profile_id=operator_profile_id,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        anonymous_session_id=anonymous_session_id,
    )

    event_metadata = dict(metadata or {})
    if outcome_reason:
        event_metadata.setdefault("funnel_outcome_reason", outcome_reason)
    event_metadata["configured_credits"] = configured_credits

    inserted = await append_billing_event(
        db,
        operator_profile_id=operator_profile_id,
        source_surface=source_surface,
        event_type=event_type,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        anonymous_session_id=anonymous_session_id,
        request_fingerprint=request_fingerprint,
        outcome_reason=outcome_reason,
        metadata=event_metadata,
        promotion_id=promotion_id,
        idempotency_key=event_idempotency_key,
    )
    if not inserted:
        return {
            "inserted": False,
            "configured_credits": configured_credits,
            "charged": False,
            "charge_error": "duplicate_event",
            "idempotency_key": event_idempotency_key,
        }

    if configured_credits <= 0:
        await db.billing_event_log.update_one(
            {"idempotency_key": event_idempotency_key},
            {
                "$set": {
                    "credits_charged": 0,
                    "currency_amount": 0,
                    "is_billable": False,
                    "updated_at": utc_now(),
                    "outcome_reason": outcome_reason,
                }
            },
        )
        return {
            "inserted": True,
            "configured_credits": configured_credits,
            "charged": False,
            "charge_error": None,
            "idempotency_key": event_idempotency_key,
        }

    _, charge_error = await consume_operator_credits(
        db,
        operator_profile_id=operator_profile_id,
        units=configured_credits,
        source_surface=source_surface,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        notes=notes or f"{source_surface}:{event_type} for {source_reference_type}:{source_reference_id}",
        billing_event_idempotency_key=event_idempotency_key,
    )

    charge_update = {
        "credits_charged": configured_credits if charge_error is None else 0,
        "currency_amount": float(currency_amount_on_success) if charge_error is None else 0,
        "is_billable": charge_error is None,
        "updated_at": utc_now(),
    }
    if charge_error is not None:
        charge_update["outcome_reason"] = charge_error
        charge_update["metadata.charge_error"] = charge_error
    elif outcome_reason:
        charge_update["outcome_reason"] = outcome_reason

    await db.billing_event_log.update_one(
        {"idempotency_key": event_idempotency_key},
        {"$set": charge_update},
    )

    return {
        "inserted": True,
        "configured_credits": configured_credits,
        "charged": charge_error is None,
        "charge_error": charge_error,
        "idempotency_key": event_idempotency_key,
    }


async def append_planner_billing_event(
    db,
    *,
    operator_profile_id: str,
    event_type: str,
    source_reference_type: str,
    source_reference_id: Optional[str],
    anonymous_session_id: Optional[str] = None,
    request_fingerprint: Optional[str] = None,
    outcome_reason: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    return await append_configurable_billing_event(
        db,
        operator_profile_id=operator_profile_id,
        source_surface="planner",
        event_type=event_type,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        anonymous_session_id=anonymous_session_id,
        request_fingerprint=request_fingerprint,
        outcome_reason=outcome_reason,
        metadata=metadata,
        notes=f"Planner event {event_type} for {source_reference_type}:{source_reference_id}",
    )


async def ensure_provider_plan(db, *, operator_profile_id: str, operator_user_id: str) -> dict:
    existing = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
    if existing:
        return existing

    free_plan = await db.billing_plans.find_one({"code": "FREE"})
    if not free_plan:
        free_plan = {
            "code": "FREE",
            "name": "Free",
            "included_credits": 0,
        }

    start_at, end_at = billing_cycle_window()
    document = {
        "operator_profile_id": operator_profile_id,
        "operator_user_id": operator_user_id,
        "plan_code": free_plan["code"],
        "plan_name": free_plan.get("name", "Free"),
        "plan_status": "active",
        "included_credits": int(free_plan.get("included_credits", 0)),
        "credits_remaining": int(free_plan.get("included_credits", 0)),
        "billing_cycle_start_at": start_at,
        "billing_cycle_end_at": end_at,
        "auto_renew": False,
        "created_at": start_at,
        "updated_at": start_at,
        "activated_at": start_at,
        "last_assignment_notes": "Auto-provisioned free plan",
        "last_assigned_by": "system",
    }
    try:
        await db.provider_plans.insert_one(document)
        return document
    except DuplicateKeyError:
        # Another request may have provisioned the profile concurrently.
        existing = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
        if existing:
            return existing
        raise


async def create_operator_plan_order(
    db,
    *,
    operator_profile_id: str,
    operator_user_id: str,
    organization_id: str,
    plan_doc: dict,
    payment_provider: str,
    client_request_id: Optional[str],
) -> tuple[dict, bool]:
    if plan_doc.get("code") == "FREE":
        raise ValueError("free_plan_not_orderable")

    if client_request_id:
        existing = await db.plan_orders.find_one(
            {
                "operator_profile_id": operator_profile_id,
                "client_request_id": client_request_id,
            }
        )
        if existing:
            return existing, False

    open_order = await db.plan_orders.find_one(
        {
            "operator_profile_id": operator_profile_id,
            "order_status": {"$in": list(PLAN_ORDER_OPEN_STATUSES)},
        },
        sort=[("created_at", -1)],
    )
    if open_order:
        raise ValueError("open_order_exists")

    subscription = await ensure_provider_plan(
        db,
        operator_profile_id=operator_profile_id,
        operator_user_id=operator_user_id,
    )
    now = utc_now()
    plan_snapshot = build_plan_snapshot(plan_doc)
    order_code = build_plan_order_code()
    order_doc = {
        "operator_profile_id": operator_profile_id,
        "operator_user_id": operator_user_id,
        "organization_id": organization_id,
        "order_code": order_code,
        "plan_code": plan_snapshot["code"],
        "plan_snapshot": plan_snapshot,
        "amount": plan_snapshot["monthly_price"],
        "currency": plan_snapshot["currency"],
        "payment_provider": payment_provider,
        "order_status": "pending_payment",
        "payment_status": "not_started",
        "fulfillment_status": "not_started",
        "client_request_id": client_request_id,
        "payment_reference": None,
        "gateway_session_id": None,
        "gateway_order_id": None,
        "gateway_payment_id": None,
        "gateway_metadata": {},
        "subscription_snapshot": {
            "plan_code": subscription.get("plan_code"),
            "plan_status": subscription.get("plan_status"),
            "credits_remaining": int(subscription.get("credits_remaining") or 0),
            "requested_plan_code": subscription.get("requested_plan_code"),
        },
        "status_history": [
            build_plan_order_history_entry(
                order_status="pending_payment",
                payment_status="not_started",
                fulfillment_status="not_started",
                actor_id=operator_user_id,
                note=f"Created order for {plan_snapshot['name']} plan",
                metadata={"payment_provider": payment_provider},
            )
        ],
        "expires_at": now + timedelta(hours=24),
        "created_at": now,
        "updated_at": now,
        "settled_at": None,
        "settled_by": None,
        "completed_at": None,
        "cancelled_at": None,
    }
    try:
        result = await db.plan_orders.insert_one(order_doc)
        order_doc["_id"] = result.inserted_id
        return order_doc, True
    except DuplicateKeyError:
        if client_request_id:
            existing = await db.plan_orders.find_one(
                {
                    "operator_profile_id": operator_profile_id,
                    "client_request_id": client_request_id,
                }
            )
            if existing:
                return existing, False

        open_order = await db.plan_orders.find_one(
            {
                "operator_profile_id": operator_profile_id,
                "order_status": {"$in": list(PLAN_ORDER_OPEN_STATUSES)},
            },
            sort=[("created_at", -1)],
        )
        if open_order:
            raise ValueError("open_order_exists")
        raise


async def append_credit_ledger_entry(
    db,
    *,
    operator_profile_id: str,
    entry_type: str,
    credits_delta: int,
    balance_after: int,
    source_surface: Optional[str],
    source_reference_type: str,
    source_reference_id: Optional[str],
    notes: Optional[str],
    created_by: Optional[str],
    idempotency_key: Optional[str] = None,
    billing_event_idempotency_key: Optional[str] = None,
) -> None:
    await db.credit_ledger.insert_one(
        {
            "idempotency_key": idempotency_key,
            "billing_event_idempotency_key": billing_event_idempotency_key,
            "operator_profile_id": operator_profile_id,
            "entry_type": entry_type,
            "credits_delta": credits_delta,
            "balance_after": balance_after,
            "source_surface": source_surface,
            "source_reference_type": source_reference_type,
            "source_reference_id": source_reference_id,
            "notes": notes,
            "created_at": utc_now(),
            "created_by": created_by,
        }
    )


async def assign_plan_to_operator(
    db,
    *,
    operator_profile_id: str,
    operator_user_id: str,
    plan_doc: dict,
    actor_id: Optional[str],
    notes: Optional[str],
    source_order_id: Optional[str] = None,
    reset_credits: bool = True,
) -> dict:
    now = utc_now()
    start_at, end_at = billing_cycle_window(now)
    existing = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
    if (
        source_order_id
        and existing
        and existing.get("last_fulfilled_order_id") == source_order_id
        and existing.get("plan_code") == plan_doc["code"]
    ):
        return existing

    current_balance = int((existing or {}).get("credits_remaining") or 0)
    included_credits = int(plan_doc.get("included_credits") or 0)
    new_balance = included_credits if reset_credits else current_balance

    update_doc = {
        "operator_profile_id": operator_profile_id,
        "operator_user_id": operator_user_id,
        "plan_code": plan_doc["code"],
        "plan_name": plan_doc["name"],
        "plan_status": "active",
        "included_credits": included_credits,
        "credits_remaining": new_balance,
        "billing_cycle_start_at": start_at,
        "billing_cycle_end_at": end_at,
        "auto_renew": False,
        "updated_at": now,
        "activated_at": now,
        "last_assignment_notes": notes,
        "last_assigned_by": actor_id,
        "requested_plan_code": None,
        "requested_plan_requested_at": None,
    }
    if source_order_id:
        update_doc["last_fulfilled_order_id"] = source_order_id
    if not existing:
        update_doc["created_at"] = now

    update_filter = {"operator_profile_id": operator_profile_id}
    if source_order_id:
        update_filter["last_fulfilled_order_id"] = {"$ne": source_order_id}

    result = await db.provider_plans.update_one(
        update_filter,
        {"$set": update_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    if source_order_id and result.modified_count == 0:
        current = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
        if current:
            return current

    delta = new_balance - current_balance
    if result.modified_count > 0 and delta != 0:
        await append_credit_ledger_entry(
            db,
            operator_profile_id=operator_profile_id,
            entry_type="grant" if delta > 0 else "adjustment",
            credits_delta=delta,
            balance_after=new_balance,
            source_surface="admin",
            source_reference_type="plan_assignment",
            source_reference_id=plan_doc["code"],
            notes=notes or f"Assigned {plan_doc['name']} plan",
            created_by=actor_id,
        )

    return await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})


async def request_plan_change(
    db,
    *,
    operator_profile_id: str,
    operator_user_id: str,
    plan_code: str,
) -> dict:
    existing = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
    if not existing:
        existing = await ensure_provider_plan(
            db,
            operator_profile_id=operator_profile_id,
            operator_user_id=operator_user_id,
        )

    await db.provider_plans.update_one(
        {"_id": existing["_id"]},
        {
            "$set": {
                "operator_user_id": operator_user_id,
                "requested_plan_code": plan_code,
                "requested_plan_requested_at": utc_now(),
                "updated_at": utc_now(),
            }
        },
    )
    return await db.provider_plans.find_one({"_id": existing["_id"]})


async def complete_operator_plan_order(
    db,
    *,
    order: dict,
    actor_id: Optional[str],
    payment_reference: Optional[str],
    gateway_payment_id: Optional[str],
    gateway_order_id: Optional[str],
    settlement_notes: Optional[str],
    gateway_metadata: Optional[dict] = None,
) -> dict:
    now = utc_now()
    if order.get("order_status") == "completed":
        return order
    if order.get("order_status") in PLAN_ORDER_TERMINAL_STATUSES - {"completed"}:
        raise ValueError("order_not_completable")

    assignment_note = build_plan_assignment_note(
        order.get("order_code", "unknown-order"),
        order.get("plan_snapshot", {}).get("name", order.get("plan_code", "plan")),
        settlement_notes,
    )

    if order.get("order_status") != "fulfillment_pending":
        history_entry = build_plan_order_history_entry(
            order_status="fulfillment_pending",
            payment_status="paid",
            fulfillment_status="pending",
            actor_id=actor_id,
            note="Payment marked as settled, preparing plan activation",
            metadata={"payment_reference": payment_reference, "gateway_payment_id": gateway_payment_id},
        )
        result = await db.plan_orders.update_one(
            {
                "_id": order["_id"],
                "order_status": {"$in": ["pending_payment", "payment_pending", "payment_received"]},
            },
            {
                "$set": {
                    "order_status": "fulfillment_pending",
                    "payment_status": "paid",
                    "fulfillment_status": "pending",
                    "payment_reference": payment_reference or order.get("payment_reference"),
                    "gateway_payment_id": gateway_payment_id or order.get("gateway_payment_id"),
                    "gateway_order_id": gateway_order_id or order.get("gateway_order_id"),
                    "gateway_metadata": gateway_metadata or order.get("gateway_metadata") or {},
                    "settled_at": now,
                    "settled_by": actor_id,
                    "updated_at": now,
                },
                "$push": {"status_history": history_entry},
            },
        )
        if result.modified_count == 0:
            refreshed = await db.plan_orders.find_one({"_id": order["_id"]})
            if refreshed and refreshed.get("order_status") == "completed":
                return refreshed
            if not refreshed or refreshed.get("order_status") in PLAN_ORDER_TERMINAL_STATUSES - {"completed"}:
                raise ValueError("order_not_completable")
            order = refreshed
        else:
            order = await db.plan_orders.find_one({"_id": order["_id"]})

    activated = await assign_plan_to_operator(
        db,
        operator_profile_id=order["operator_profile_id"],
        operator_user_id=order["operator_user_id"],
        plan_doc=order["plan_snapshot"],
        actor_id=actor_id,
        notes=assignment_note,
        source_order_id=str(order["_id"]),
        reset_credits=True,
    )

    history_entry = build_plan_order_history_entry(
        order_status="completed",
        payment_status="paid",
        fulfillment_status="completed",
        actor_id=actor_id,
        note="Plan order completed and credits activated",
        metadata={"subscription_plan_code": activated.get("plan_code")},
    )
    completion_result = await db.plan_orders.update_one(
        {"_id": order["_id"], "order_status": {"$ne": "completed"}},
        {
            "$set": {
                "order_status": "completed",
                "payment_status": "paid",
                "fulfillment_status": "completed",
                "payment_reference": payment_reference or order.get("payment_reference"),
                "gateway_payment_id": gateway_payment_id or order.get("gateway_payment_id"),
                "gateway_order_id": gateway_order_id or order.get("gateway_order_id"),
                "gateway_metadata": gateway_metadata or order.get("gateway_metadata") or {},
                "completed_at": now,
                "updated_at": now,
            },
            "$push": {"status_history": history_entry},
        },
    )
    if completion_result.modified_count == 0:
        return await db.plan_orders.find_one({"_id": order["_id"]})
    return await db.plan_orders.find_one({"_id": order["_id"]})


async def apply_credit_adjustment(
    db,
    *,
    operator_profile_id: str,
    credits_delta: int,
    notes: str,
    actor_id: Optional[str],
) -> dict:
    plan = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
    if not plan:
        raise ValueError("Provider plan not found")

    current_balance = int(plan.get("credits_remaining") or 0)
    new_balance = current_balance + credits_delta
    if new_balance < 0:
        raise ValueError("Adjustment would make credit balance negative")

    await db.provider_plans.update_one(
        {"_id": plan["_id"]},
        {"$set": {"credits_remaining": new_balance, "updated_at": utc_now()}},
    )
    await append_credit_ledger_entry(
        db,
        operator_profile_id=operator_profile_id,
        entry_type="adjustment",
        credits_delta=credits_delta,
        balance_after=new_balance,
        source_surface="admin",
        source_reference_type="manual_adjustment",
        source_reference_id=None,
        notes=notes,
        created_by=actor_id,
    )
    plan["credits_remaining"] = new_balance
    return plan


async def consume_operator_credits(
    db,
    *,
    operator_profile_id: str,
    units: int,
    source_surface: str,
    source_reference_type: str,
    source_reference_id: Optional[str],
    notes: Optional[str],
    billing_event_idempotency_key: Optional[str] = None,
) -> tuple[Optional[dict], Optional[str]]:
    plan = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
    if not plan or plan.get("plan_status") != "active":
        return None, "no_active_plan"

    current_balance = int(plan.get("credits_remaining") or 0)
    if current_balance < units:
        return plan, "insufficient_credits"

    new_balance = current_balance - units
    result = await db.provider_plans.update_one(
        {
            "_id": plan["_id"],
            "credits_remaining": {"$gte": units},
            "plan_status": "active",
        },
        {
            "$inc": {"credits_remaining": -units},
            "$set": {"updated_at": utc_now()},
        },
    )
    if result.modified_count == 0:
        return plan, "insufficient_credits"

    await append_credit_ledger_entry(
        db,
        operator_profile_id=operator_profile_id,
        entry_type="debit",
        credits_delta=-units,
        balance_after=new_balance,
        source_surface=source_surface,
        source_reference_type=source_reference_type,
        source_reference_id=source_reference_id,
        notes=notes,
        created_by="system",
        billing_event_idempotency_key=billing_event_idempotency_key,
    )

    plan["credits_remaining"] = new_balance
    return plan, None


async def expire_stale_plan_orders(
    db,
    *,
    now: Optional[datetime] = None,
    limit: int = 500,
    actor_id: str = "system:expiry",
) -> dict:
    effective_now = now or utc_now()
    target_statuses = ["pending_payment", "payment_pending"]
    stale_orders = await db.plan_orders.find(
        {
            "order_status": {"$in": target_statuses},
            "expires_at": {"$lt": effective_now},
        }
    ).limit(max(1, min(limit, 2000))).to_list(length=max(1, min(limit, 2000)))

    if not stale_orders:
        return {"matched": 0, "expired": 0}

    expired = 0
    for order in stale_orders:
        result = await db.plan_orders.update_one(
            {
                "_id": order["_id"],
                "order_status": {"$in": target_statuses},
                "expires_at": {"$lt": effective_now},
            },
            {
                "$set": {
                    "order_status": "expired",
                    "payment_status": "cancelled",
                    "updated_at": effective_now,
                },
                "$push": {
                    "status_history": {
                        "timestamp": effective_now,
                        "order_status": "expired",
                        "payment_status": "cancelled",
                        "fulfillment_status": order.get("fulfillment_status", "not_started"),
                        "actor_id": actor_id,
                        "note": "Plan order expired due to stale unpaid state",
                        "metadata": {"expires_at": order.get("expires_at")},
                    }
                },
            },
        )
        if result.modified_count > 0:
            expired += 1

    return {"matched": len(stale_orders), "expired": expired}


async def apply_webhook_event_to_order(
    db,
    *,
    order: dict,
    provider: str,
    event_id: Optional[str],
    event_type: str,
    payment_reference: Optional[str],
    gateway_payment_id: Optional[str],
    gateway_order_id: Optional[str],
    actor_id: str = "system:webhook",
    note_prefix: str = "Payment provider webhook",
) -> bool:
    provider_key = (provider or "").strip().lower()
    event_type_value = str(event_type or "")
    now = utc_now()

    if is_payment_success_event(provider=provider_key, event_type=event_type_value):
        update_result = await db.plan_orders.update_one(
            {"_id": order["_id"], "order_status": {"$in": ["pending_payment", "payment_pending"]}},
            {
                "$set": {
                    "order_status": "payment_received",
                    "payment_status": "authorized",
                    "payment_reference": payment_reference or order.get("payment_reference"),
                    "gateway_payment_id": gateway_payment_id or order.get("gateway_payment_id"),
                    "gateway_order_id": gateway_order_id or order.get("gateway_order_id"),
                    "updated_at": now,
                },
                "$push": {
                    "status_history": {
                        "timestamp": now,
                        "order_status": "payment_received",
                        "payment_status": "authorized",
                        "fulfillment_status": order.get("fulfillment_status", "not_started"),
                        "actor_id": actor_id,
                        "note": f"{note_prefix} accepted: {provider_key}",
                        "metadata": {
                            "provider": provider_key,
                            "event_id": event_id,
                            "event_type": event_type_value,
                        },
                    }
                },
            },
        )
        return update_result.modified_count > 0

    if is_payment_failure_event(provider=provider_key, event_type=event_type_value):
        update_result = await db.plan_orders.update_one(
            {"_id": order["_id"], "order_status": {"$in": ["pending_payment", "payment_pending", "payment_received"]}},
            {
                "$set": {
                    "order_status": "failed",
                    "payment_status": "failed",
                    "payment_reference": payment_reference or order.get("payment_reference"),
                    "gateway_payment_id": gateway_payment_id or order.get("gateway_payment_id"),
                    "gateway_order_id": gateway_order_id or order.get("gateway_order_id"),
                    "updated_at": now,
                },
                "$push": {
                    "status_history": {
                        "timestamp": now,
                        "order_status": "failed",
                        "payment_status": "failed",
                        "fulfillment_status": order.get("fulfillment_status", "not_started"),
                        "actor_id": actor_id,
                        "note": f"{note_prefix} marked payment failed: {provider_key}",
                        "metadata": {
                            "provider": provider_key,
                            "event_id": event_id,
                            "event_type": event_type_value,
                        },
                    }
                },
            },
        )
        return update_result.modified_count > 0

    if is_payment_refund_event(provider=provider_key, event_type=event_type_value):
        next_order_status = "completed" if order.get("order_status") == "completed" else "failed"
        next_fulfillment_status = "completed" if order.get("fulfillment_status") == "completed" else "not_started"
        update_result = await db.plan_orders.update_one(
            {"_id": order["_id"], "payment_status": {"$ne": "refunded"}},
            {
                "$set": {
                    "order_status": next_order_status,
                    "payment_status": "refunded",
                    "payment_reference": payment_reference or order.get("payment_reference"),
                    "gateway_payment_id": gateway_payment_id or order.get("gateway_payment_id"),
                    "gateway_order_id": gateway_order_id or order.get("gateway_order_id"),
                    "updated_at": now,
                },
                "$push": {
                    "status_history": {
                        "timestamp": now,
                        "order_status": next_order_status,
                        "payment_status": "refunded",
                        "fulfillment_status": next_fulfillment_status,
                        "actor_id": actor_id,
                        "note": f"{note_prefix} marked refund: {provider_key}",
                        "metadata": {
                            "provider": provider_key,
                            "event_id": event_id,
                            "event_type": event_type_value,
                        },
                    }
                },
            },
        )
        return update_result.modified_count > 0

    return False


async def apply_refund_credit_compensation(
    db,
    *,
    order: dict,
    actor_id: Optional[str],
    notes: Optional[str],
) -> dict:
    if not order:
        raise ValueError("order_not_found")
    if order.get("payment_status") != "refunded" or order.get("order_status") != "completed":
        raise ValueError("order_not_refund_completed")

    source_reference_id = str(order["_id"])
    processing_now = utc_now()
    lock_result = await db.plan_orders.update_one(
        {
            "_id": order["_id"],
            "order_status": "completed",
            "payment_status": "refunded",
            "refund_compensation_applied": {"$ne": True},
            "refund_compensation_state": {"$ne": "processing"},
        },
        {
            "$set": {
                "refund_compensation_state": "processing",
                "refund_compensation_started_at": processing_now,
                "refund_compensation_started_by": actor_id,
                "updated_at": processing_now,
            }
        },
    )

    if lock_result.modified_count == 0:
        current = await db.plan_orders.find_one({"_id": order["_id"]})
        if current and current.get("refund_compensation_applied") is True:
            await db.plan_orders.update_one(
                {"_id": order["_id"]},
                {
                    "$inc": {"refund_compensation_duplicate_attempts": 1},
                    "$set": {
                        "refund_compensation_last_duplicate_attempt_at": utc_now(),
                        "refund_compensation_last_duplicate_attempt_by": actor_id,
                        "updated_at": utc_now(),
                    },
                },
            )
            return {
                "applied": False,
                "reason": "already_compensated",
                "credits_delta": int(current.get("refund_compensation_credits") or 0),
            }
        if current and current.get("refund_compensation_state") == "processing":
            await db.plan_orders.update_one(
                {"_id": order["_id"]},
                {
                    "$inc": {"refund_compensation_duplicate_attempts": 1},
                    "$set": {
                        "refund_compensation_last_duplicate_attempt_at": utc_now(),
                        "refund_compensation_last_duplicate_attempt_by": actor_id,
                        "updated_at": utc_now(),
                    },
                },
            )
            return {
                "applied": False,
                "reason": "compensation_in_progress",
                "credits_delta": int(current.get("refund_compensation_credits") or 0),
            }
        raise ValueError("order_not_refund_completed")

    try:
        credits_delta = int((order.get("plan_snapshot") or {}).get("included_credits") or 0)
        if credits_delta <= 0:
            raise ValueError("no_compensation_credits")

        plan = await db.provider_plans.find_one({"operator_profile_id": order["operator_profile_id"]})
        if not plan:
            raise ValueError("provider_plan_not_found")

        current_balance = int(plan.get("credits_remaining") or 0)
        new_balance = current_balance + credits_delta
        now = utc_now()
        await db.provider_plans.update_one(
            {"_id": plan["_id"]},
            {"$set": {"credits_remaining": new_balance, "updated_at": now}},
        )

        compensation_notes = notes or f"Refund compensation for order {order.get('order_code') or source_reference_id}"
        await append_credit_ledger_entry(
            db,
            operator_profile_id=order["operator_profile_id"],
            entry_type="refund",
            credits_delta=credits_delta,
            balance_after=new_balance,
            source_surface="admin",
            source_reference_type="refund_compensation",
            source_reference_id=source_reference_id,
            notes=compensation_notes,
            created_by=actor_id,
            idempotency_key=f"refund_compensation:{source_reference_id}",
        )
        await db.plan_orders.update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "refund_compensation_applied": True,
                    "refund_compensation_state": "applied",
                    "refund_compensation_credits": credits_delta,
                    "refund_compensation_at": now,
                    "refund_compensation_by": actor_id,
                    "updated_at": now,
                },
                "$push": {
                    "status_history": {
                        "timestamp": now,
                        "order_status": order.get("order_status", "completed"),
                        "payment_status": order.get("payment_status", "refunded"),
                        "fulfillment_status": order.get("fulfillment_status", "completed"),
                        "actor_id": actor_id,
                        "note": "Applied refund compensation credits",
                        "metadata": {"credits_delta": credits_delta},
                    }
                },
            },
        )

        return {
            "applied": True,
            "reason": None,
            "credits_delta": credits_delta,
            "balance_after": new_balance,
        }
    except Exception as exc:
        await db.plan_orders.update_one(
            {"_id": order["_id"], "refund_compensation_state": "processing"},
            {
                "$set": {
                    "refund_compensation_state": "failed",
                    "refund_compensation_failed_at": utc_now(),
                    "refund_compensation_error": str(exc),
                    "updated_at": utc_now(),
                }
            },
        )
        raise


def is_billing_event_debit_mismatch(*, event: dict, ledger_entry: Optional[dict]) -> bool:
    if not event.get("is_billable"):
        return False
    if not ledger_entry:
        return True
    credits_charged = int(event.get("credits_charged") or 0)
    credits_delta = int(ledger_entry.get("credits_delta") or 0)
    return credits_delta != (-1 * credits_charged)


async def build_credit_event_reconciliation_report(
    db,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> dict:
    max_items = max(1, min(limit, 2000))
    events = await db.billing_event_log.find({}).sort([("created_at", -1), ("_id", -1)]).limit(max_items).to_list(length=max_items)
    debits = await db.credit_ledger.find({"entry_type": "debit"}).sort([("created_at", -1), ("_id", -1)]).limit(max_items * 4).to_list(length=max_items * 4)

    if since is not None:
        events = [row for row in events if row.get("created_at") and row.get("created_at") >= since]
        debits = [row for row in debits if row.get("created_at") and row.get("created_at") >= since]

    debits_by_event_key: dict[str, list[dict]] = {}
    for row in debits:
        key = row.get("billing_event_idempotency_key")
        if not isinstance(key, str) or not key:
            continue
        debits_by_event_key.setdefault(key, []).append(row)

    missing_or_mismatched: list[dict] = []
    matched_event_keys: set[str] = set()
    billable_events_count = 0

    for event in events:
        if not event.get("is_billable"):
            continue
        billable_events_count += 1
        event_key = str(event.get("idempotency_key") or "")
        if not event_key:
            missing_or_mismatched.append(
                {
                    "type": "missing_event_idempotency_key",
                    "operator_profile_id": event.get("operator_profile_id"),
                    "event": event,
                    "ledger": None,
                }
            )
            continue

        linked_debits = debits_by_event_key.get(event_key, [])
        if linked_debits:
            matched_event_keys.add(event_key)

        if not linked_debits:
            missing_or_mismatched.append(
                {
                    "type": "missing_debit",
                    "operator_profile_id": event.get("operator_profile_id"),
                    "event": event,
                    "ledger": None,
                }
            )
            continue

        if len(linked_debits) > 1:
            missing_or_mismatched.append(
                {
                    "type": "duplicate_debits",
                    "operator_profile_id": event.get("operator_profile_id"),
                    "event": event,
                    "ledger": linked_debits,
                }
            )
            continue

        ledger = linked_debits[0]
        if is_billing_event_debit_mismatch(event=event, ledger_entry=ledger):
            missing_or_mismatched.append(
                {
                    "type": "credit_mismatch",
                    "operator_profile_id": event.get("operator_profile_id"),
                    "event": event,
                    "ledger": ledger,
                }
            )

    orphan_debits: list[dict] = []
    for row in debits:
        key = row.get("billing_event_idempotency_key")
        if not isinstance(key, str) or not key:
            continue
        if key not in matched_event_keys:
            orphan_debits.append(row)

    return {
        "billable_events": billable_events_count,
        "issues": missing_or_mismatched,
        "orphan_debits": orphan_debits,
        "issue_count": len(missing_or_mismatched),
        "orphan_debit_count": len(orphan_debits),
    }


async def repair_credit_event_mismatches(
    db,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
    max_repairs: int = 200,
) -> dict:
    report = await build_credit_event_reconciliation_report(db, since=since, limit=limit)
    repaired = 0
    unresolved_missing_debits = 0
    unresolved_orphan_debits = 0
    skipped_duplicate_debits = 0
    repaired_event_keys: list[str] = []

    async def _repair_event_from_debit(*, event_key: str, debit: dict, source_note: str) -> bool:
        nonlocal repaired
        if repaired >= max(1, max_repairs):
            return False

        event = await db.billing_event_log.find_one({"idempotency_key": event_key})
        if not event:
            return False

        credits_charged = abs(int(debit.get("credits_delta") or 0))
        now = utc_now()
        await db.billing_event_log.update_one(
            {"_id": event["_id"]},
            {
                "$set": {
                    "is_billable": True,
                    "credits_charged": credits_charged,
                    "updated_at": now,
                    "metadata.reconciliation_repaired": True,
                    "metadata.reconciliation_repair_source": source_note,
                    "metadata.reconciliation_repaired_at": now.isoformat(),
                }
            },
        )
        repaired += 1
        repaired_event_keys.append(event_key)
        return True

    for issue in report.get("issues", []):
        issue_type = issue.get("type")
        if issue_type == "missing_debit":
            unresolved_missing_debits += 1
            continue
        if issue_type == "duplicate_debits":
            skipped_duplicate_debits += 1
            continue
        if issue_type == "credit_mismatch":
            event = issue.get("event") or {}
            ledger = issue.get("ledger") or {}
            event_key = str(event.get("idempotency_key") or "")
            if not event_key or not ledger:
                unresolved_missing_debits += 1
                continue
            repaired_ok = await _repair_event_from_debit(
                event_key=event_key,
                debit=ledger,
                source_note="credit_mismatch",
            )
            if not repaired_ok:
                unresolved_missing_debits += 1

    for debit in report.get("orphan_debits", []):
        event_key = str(debit.get("billing_event_idempotency_key") or "")
        if not event_key:
            unresolved_orphan_debits += 1
            continue
        repaired_ok = await _repair_event_from_debit(
            event_key=event_key,
            debit=debit,
            source_note="orphan_debit",
        )
        if not repaired_ok:
            unresolved_orphan_debits += 1

    post_report = await build_credit_event_reconciliation_report(db, since=since, limit=limit)
    return {
        "repaired": repaired,
        "repaired_event_keys": repaired_event_keys,
        "unresolved_missing_debits": unresolved_missing_debits,
        "unresolved_orphan_debits": unresolved_orphan_debits,
        "skipped_duplicate_debits": skipped_duplicate_debits,
        "before": report,
        "after": post_report,
    }


async def build_credit_anomaly_counters(
    db,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> dict:
    report = await build_credit_event_reconciliation_report(db, since=since, limit=limit)

    orders = await db.plan_orders.find({}).to_list(length=5000)
    if since is not None:
        def _is_since(value: object) -> bool:
            return isinstance(value, datetime) and value >= since

        orders = [
            row for row in orders if (
                _is_since(row.get("updated_at"))
                or _is_since(row.get("refund_compensation_failed_at"))
                or _is_since(row.get("refund_compensation_last_duplicate_attempt_at"))
            )
        ]

    duplicate_attempt_count = 0
    compensation_failure_count = 0
    compensation_processing_count = 0
    for order in orders:
        duplicate_attempt_count += int(order.get("refund_compensation_duplicate_attempts") or 0)
        state = str(order.get("refund_compensation_state") or "").strip().lower()
        if state == "failed":
            compensation_failure_count += 1
        elif state == "processing":
            compensation_processing_count += 1

    issue_types: dict[str, int] = {
        "missing_debit": 0,
        "duplicate_debits": 0,
        "credit_mismatch": 0,
        "missing_event_idempotency_key": 0,
    }
    for issue in report.get("issues", []):
        issue_type = str(issue.get("type") or "")
        if issue_type in issue_types:
            issue_types[issue_type] += 1

    mismatch_count = int(report.get("issue_count") or 0) + int(report.get("orphan_debit_count") or 0)

    return {
        "duplicate_attempt_count": duplicate_attempt_count,
        "compensation_failure_count": compensation_failure_count,
        "compensation_processing_count": compensation_processing_count,
        "mismatch_count": mismatch_count,
        "mismatch_breakdown": {
            **issue_types,
            "orphan_debits": int(report.get("orphan_debit_count") or 0),
        },
        "reconciliation_scan": {
            "billable_events": int(report.get("billable_events") or 0),
            "issue_count": int(report.get("issue_count") or 0),
            "orphan_debit_count": int(report.get("orphan_debit_count") or 0),
        },
    }