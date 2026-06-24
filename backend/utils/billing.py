from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from ..config import settings


SEARCH_CLICK_DEDUPE_MINUTES = 30
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
    now = current_time or utc_now()
    bucket_minutes = (now.hour * 60 + now.minute) // SEARCH_CLICK_DEDUPE_MINUTES
    fingerprint = session_id or request_id or "|".join([
        client_host or "unknown-host",
        (user_agent or "unknown-agent")[:120],
    ])
    raw = "|".join([
        promotion_id,
        source,
        fingerprint,
        now.strftime("%Y-%m-%d"),
        str(bucket_minutes),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    await db.provider_plans.insert_one(document)
    return document


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
    result = await db.plan_orders.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id
    return order_doc, True


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
) -> None:
    await db.credit_ledger.insert_one(
        {
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
    reset_credits: bool = True,
) -> dict:
    now = utc_now()
    start_at, end_at = billing_cycle_window(now)
    existing = await db.provider_plans.find_one({"operator_profile_id": operator_profile_id})
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
    if not existing:
        update_doc["created_at"] = now

    await db.provider_plans.update_one(
        {"operator_profile_id": operator_profile_id},
        {"$set": update_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    delta = new_balance - current_balance
    if delta != 0:
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

    subscription = await db.provider_plans.find_one({"operator_profile_id": order["operator_profile_id"]})
    if subscription and subscription.get("last_assignment_notes") == assignment_note and subscription.get("plan_code") == order.get("plan_code"):
        activated = subscription
    else:
        activated = await assign_plan_to_operator(
            db,
            operator_profile_id=order["operator_profile_id"],
            operator_user_id=order["operator_user_id"],
            plan_doc=order["plan_snapshot"],
            actor_id=actor_id,
            notes=assignment_note,
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
    await db.plan_orders.update_one(
        {"_id": order["_id"]},
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
    )

    plan["credits_remaining"] = new_balance
    return plan, None