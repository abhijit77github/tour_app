from datetime import datetime, timedelta, timezone
import csv
import io

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse

from ..database import get_database
from ..models.billing import (
    BillingPlanCreate,
    BillingPlanUpdate,
    CreditAdjustmentRequest,
    PlanOrderSettlementRequest,
    PlannerPricingSettingsUpdate,
    RefundCreditCompensationRequest,
    ProviderPlanAssignRequest,
)
from ..models.planner_quota import PlannerTouristQuotaSettingsUpdate
from ..routers.admin import get_current_admin
from ..utils.billing import (
    PLANNER_BILLING_SETTINGS_KEY,
    apply_refund_credit_compensation,
    apply_webhook_event_to_order,
    apply_credit_adjustment,
    assign_plan_to_operator,
    build_credit_anomaly_counters,
    build_credit_event_reconciliation_report,
    complete_operator_plan_order,
    expire_stale_plan_orders,
    get_planner_pricing_settings_document,
    repair_credit_event_mismatches,
)
from ..utils.planner_quota import PLANNER_TOURIST_QUOTA_SETTINGS_KEY, get_planner_tourist_quota_settings_document

router = APIRouter(prefix="/admin/billing", tags=["Admin Billing"])


def _serialize_document(doc: dict) -> dict:
    doc = dict(doc)
    if doc.get("_id") is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _empty_surface_summary(surface: str) -> dict:
    return {
        "surface": surface,
        "events": 0,
        "billable_events": 0,
        "non_billable_events": 0,
        "credits_consumed": 0,
        "spend_amount": 0,
    }


def _empty_planner_summary() -> dict:
    return {
        "totals": {
            "events": 0,
            "billable_events": 0,
            "non_billable_events": 0,
            "credits_consumed": 0,
            "spend_amount": 0,
        },
        "funnel": {
            "recommendations_served": 0,
            "quote_intents": 0,
            "itinerary_saves": 0,
        },
        "pricing": {"search_profile_click": 1, "planner_intent_click": 0, "qualified_lead": 0, "conversion": 0},
        "by_event_type": [],
    }


def _serialize_pricing_settings(document: dict) -> dict:
    return {
        "values": document.get("values", {"search_profile_click": 1, "planner_intent_click": 0, "qualified_lead": 0, "conversion": 0}),
        "source": document.get("source", "environment"),
        "updated_at": document.get("updated_at"),
        "updated_by": document.get("updated_by"),
    }


def _serialize_quota_settings(document: dict) -> dict:
    defaults = {
        "daily_limit": 3,
        "monthly_limit": 10,
        "ad_reward_daily_credits": 1,
        "ad_reward_monthly_credits": 1,
        "promotion_reward_daily_credits": 1,
        "promotion_reward_monthly_credits": 2,
    }
    return {
        "values": document.get("values", defaults),
        "source": document.get("source", "environment"),
        "updated_at": document.get("updated_at"),
        "updated_by": document.get("updated_by"),
    }


def _serialize_pricing_history_entry(doc: dict) -> dict:
    return {
        "_id": str(doc.get("_id")) if doc.get("_id") is not None else None,
        "key": doc.get("key"),
        "previous_value": doc.get("previous_value", {}),
        "new_value": doc.get("new_value", {}),
        "changed_by": doc.get("changed_by"),
        "changed_at": doc.get("changed_at"),
        "change_reason": doc.get("change_reason"),
    }


def _serialize_plan_order(doc: dict) -> dict:
    serialized = _serialize_document(doc)
    if serialized.get("status_history"):
        normalized_history = []
        for item in serialized["status_history"]:
            normalized = dict(item)
            normalized_history.append(normalized)
        serialized["status_history"] = normalized_history
    return serialized


async def _find_related_webhook_event(db, *, order: dict, payload: PlanOrderSettlementRequest) -> dict | None:
    lookup_values = [
        ("event_id", payload.gateway_payment_id),
        ("gateway_payment_id", payload.gateway_payment_id),
        ("gateway_order_id", payload.gateway_order_id),
        ("payment_reference", payload.payment_reference),
        ("order_code", order.get("order_code")),
        ("gateway_order_id", order.get("gateway_order_id")),
        ("gateway_payment_id", order.get("gateway_payment_id")),
        ("payment_reference", order.get("payment_reference")),
    ]
    for key, value in lookup_values:
        if not value:
            continue
        matched = await db.billing_webhook_events.find_one({key: value}, sort=[("created_at", -1)])
        if matched:
            return matched
    return None


def _build_settlement_gateway_metadata(base_metadata: dict, webhook_event: dict | None) -> dict:
    merged = dict(base_metadata or {})
    if not webhook_event:
        return merged

    merged.setdefault("settlement_source", "webhook")
    merged.setdefault("webhook_event_id", webhook_event.get("event_id"))
    merged.setdefault("webhook_provider", webhook_event.get("provider"))
    merged.setdefault("webhook_event_type", webhook_event.get("event_type"))
    merged.setdefault("webhook_idempotency_key", webhook_event.get("idempotency_key"))
    return merged


async def _attach_tourist_identity(db, doc: dict) -> dict:
    serialized = _serialize_document(doc)
    tourist_user = await db.users.find_one({"_id": ObjectId(serialized["user_id"])}) if serialized.get("user_id") and ObjectId.is_valid(serialized["user_id"]) else None
    serialized["tourist_user"] = {
        "email": (tourist_user or {}).get("email"),
        "full_name": (tourist_user or {}).get("full_name"),
    }
    return serialized


@router.get("/plans")
async def list_billing_plans(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    _ = admin
    plans = []
    cursor = db.billing_plans.find().sort([("monthly_price", 1), ("code", 1)])
    async for plan in cursor:
        plans.append(_serialize_document(plan))
    return {"plans": plans, "count": len(plans)}


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_billing_plan(
    payload: BillingPlanCreate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    data = payload.model_dump()
    existing = await db.billing_plans.find_one({"code": data["code"]})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing plan code already exists")

    data["created_at"] = data["updated_at"] = admin_created_at = datetime.now(timezone.utc)
    data["created_by"] = admin.get("_id")
    result = await db.billing_plans.insert_one(data)
    data["_id"] = result.inserted_id
    return {"message": "Billing plan created", "plan": _serialize_document(data)}


@router.patch("/plans/{plan_id}")
async def update_billing_plan(
    plan_id: str,
    updates: BillingPlanUpdate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    update_data = {key: value for key, value in updates.model_dump().items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["updated_by"] = admin.get("_id")
    try:
        result = await db.billing_plans.update_one({"_id": ObjectId(plan_id)}, {"$set": update_data})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid billing plan ID") from exc
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing plan not found")
    updated = await db.billing_plans.find_one({"_id": ObjectId(plan_id)})
    return {"message": "Billing plan updated", "plan": _serialize_document(updated)}


@router.get("/subscriptions")
async def list_provider_subscriptions(
    operator_profile_id: str | None = None,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if operator_profile_id:
        query["operator_profile_id"] = operator_profile_id

    rows = []
    cursor = db.provider_plans.find(query).sort("updated_at", -1)
    async for row in cursor:
        operator_profile = None
        try:
            operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(row["operator_profile_id"])})
        except Exception:
            operator_profile = None
        serialized = _serialize_document(row)
        serialized["operator_profile"] = {
            "business_name": (operator_profile or {}).get("business_name"),
        }
        rows.append(serialized)

    return {"subscriptions": rows, "count": len(rows)}


@router.post("/subscriptions/{operator_profile_id}/assign")
async def assign_provider_subscription(
    operator_profile_id: str,
    payload: ProviderPlanAssignRequest,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    try:
        operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(operator_profile_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operator profile ID") from exc
    if not operator_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    plan_doc = await db.billing_plans.find_one({"code": payload.plan_code, "is_active": True})
    if not plan_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing plan not found or inactive")

    subscription = await assign_plan_to_operator(
        db,
        operator_profile_id=str(operator_profile["_id"]),
        operator_user_id=str(operator_profile.get("user_id") or ""),
        plan_doc=plan_doc,
        actor_id=admin.get("_id"),
        notes=payload.notes,
        reset_credits=payload.reset_credits,
    )
    return {"message": "Provider plan assigned", "subscription": _serialize_document(subscription)}


@router.get("/plan-orders")
async def list_plan_orders(
    order_status: str | None = None,
    payment_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if order_status:
        query["order_status"] = order_status
    if payment_status:
        query["payment_status"] = payment_status

    rows = []
    cursor = db.plan_orders.find(query).sort("created_at", -1).limit(limit)
    async for row in cursor:
        operator_profile = None
        try:
            operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(row["operator_profile_id"])})
        except Exception:
            operator_profile = None
        serialized = _serialize_plan_order(row)
        serialized["operator_profile"] = {
            "business_name": (operator_profile or {}).get("business_name"),
        }
        rows.append(serialized)
    return {"orders": rows, "count": len(rows)}


@router.post("/plan-orders/{order_id}/complete")
async def complete_plan_order(
    order_id: str,
    payload: PlanOrderSettlementRequest,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    try:
        order = await db.plan_orders.find_one({"_id": ObjectId(order_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id") from exc

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan order not found")

    webhook_event = await _find_related_webhook_event(db, order=order, payload=payload)
    payment_reference = payload.payment_reference or (webhook_event or {}).get("payment_reference")
    gateway_payment_id = payload.gateway_payment_id or (webhook_event or {}).get("gateway_payment_id")
    gateway_order_id = payload.gateway_order_id or (webhook_event or {}).get("gateway_order_id")
    gateway_metadata = _build_settlement_gateway_metadata(payload.gateway_metadata, webhook_event)

    try:
        completed = await complete_operator_plan_order(
            db,
            order=order,
            actor_id=admin.get("_id"),
            payment_reference=payment_reference,
            gateway_payment_id=gateway_payment_id,
            gateway_order_id=gateway_order_id,
            settlement_notes=payload.settlement_notes,
            gateway_metadata=gateway_metadata,
        )
    except ValueError as exc:
        if str(exc) == "order_not_completable":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan order is not in a completable state") from exc
        raise

    return {
        "message": "Plan order settled and provider credits activated",
        "order": _serialize_plan_order(completed),
    }


@router.get("/webhook-events")
async def list_billing_webhook_events(
    provider: str | None = None,
    order_code: str | None = None,
    event_id: str | None = None,
    processed: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if provider:
        query["provider"] = provider.strip().lower()
    if order_code:
        query["order_code"] = order_code
    if event_id:
        query["event_id"] = event_id
    if processed is not None:
        query["processed"] = processed

    rows = []
    docs = await db.billing_webhook_events.find(query).sort([("created_at", -1), ("_id", -1)]).limit(limit).to_list(length=limit)
    for row in docs:
        rows.append(_serialize_document(row))
    return {"events": rows, "count": len(rows)}


@router.get("/webhook-events/{idempotency_key}")
async def get_billing_webhook_event(
    idempotency_key: str,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    event = await db.billing_webhook_events.find_one({"idempotency_key": idempotency_key})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook event not found")
    return {"event": _serialize_document(event)}


@router.post("/webhook-events/{idempotency_key}/reprocess")
async def reprocess_billing_webhook_event(
    idempotency_key: str,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    event = await db.billing_webhook_events.find_one({"idempotency_key": idempotency_key})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook event not found")

    order = None
    if event.get("order_code"):
        order = await db.plan_orders.find_one({"order_code": event.get("order_code")})
    if not order and event.get("gateway_order_id"):
        order = await db.plan_orders.find_one({"gateway_order_id": event.get("gateway_order_id")})

    order_update_applied = False
    if order:
        order_update_applied = await apply_webhook_event_to_order(
            db,
            order=order,
            provider=str(event.get("provider") or ""),
            event_id=event.get("event_id"),
            event_type=str(event.get("event_type") or ""),
            payment_reference=event.get("payment_reference"),
            gateway_payment_id=event.get("gateway_payment_id"),
            gateway_order_id=event.get("gateway_order_id"),
            actor_id=f"admin:{admin.get('_id')}",
            note_prefix="Admin webhook replay",
        )

    replayed_at = datetime.now(timezone.utc)
    await db.billing_webhook_events.update_one(
        {"_id": event["_id"]},
        {
            "$set": {
                "processed": True,
                "processed_at": replayed_at,
                "order_found": bool(order),
                "order_update_applied": order_update_applied,
                "last_reprocessed_at": replayed_at,
                "last_reprocessed_by": admin.get("_id"),
                "updated_at": replayed_at,
            },
            "$push": {
                "reprocess_history": {
                    "timestamp": replayed_at,
                    "actor_id": admin.get("_id"),
                    "order_found": bool(order),
                    "order_update_applied": order_update_applied,
                }
            },
        },
    )
    refreshed_event = await db.billing_webhook_events.find_one({"_id": event["_id"]})

    return {
        "message": "Webhook event reprocess completed",
        "event": _serialize_document(refreshed_event),
        "order_found": bool(order),
        "order_update_applied": order_update_applied,
    }


@router.post("/plan-orders/expire-stale")
async def expire_stale_orders(
    limit: int = Query(default=500, ge=1, le=2000),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    result = await expire_stale_plan_orders(db, limit=limit)
    return {
        "message": "Stale plan-order expiry run completed",
        "matched": result.get("matched", 0),
        "expired": result.get("expired", 0),
    }


@router.post("/plan-orders/{order_id}/refund-compensation")
async def apply_refund_compensation(
    order_id: str,
    payload: RefundCreditCompensationRequest,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    try:
        order = await db.plan_orders.find_one({"_id": ObjectId(order_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id") from exc

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan order not found")

    try:
        result = await apply_refund_credit_compensation(
            db,
            order=order,
            actor_id=admin.get("_id"),
            notes=payload.notes,
        )
    except ValueError as exc:
        reason = str(exc)
        if reason == "order_not_refund_completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must be completed with refunded payment status") from exc
        if reason == "provider_plan_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider plan not found for operator") from exc
        if reason == "no_compensation_credits":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order plan has no compensation credits") from exc
        raise

    subscription = await db.provider_plans.find_one({"operator_profile_id": order.get("operator_profile_id")})
    message = "Refund compensation processed"
    if not result.get("applied"):
        reason = result.get("reason")
        if reason == "already_compensated":
            message = "Refund compensation already applied"
        elif reason == "compensation_in_progress":
            message = "Refund compensation is currently in progress"
        else:
            message = "Refund compensation not applied"

    return {
        "message": message,
        "result": result,
        "subscription": _serialize_document(subscription) if subscription else None,
    }


@router.get("/ledger")
async def list_credit_ledger(
    operator_profile_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if operator_profile_id:
        query["operator_profile_id"] = operator_profile_id
    rows = []
    cursor = db.credit_ledger.find(query).sort("created_at", -1).limit(limit)
    async for row in cursor:
        rows.append(_serialize_document(row))
    return {"entries": rows, "count": len(rows)}


@router.get("/planner-pricing")
async def get_planner_pricing_settings(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    _ = admin
    document = await get_planner_pricing_settings_document(db)
    return {"settings": _serialize_pricing_settings(document)}


@router.post("/planner-pricing")
async def save_planner_pricing_settings(
    payload: PlannerPricingSettingsUpdate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    now = datetime.now(timezone.utc)
    value = payload.model_dump()
    existing = await db.admin_settings.find_one({"key": PLANNER_BILLING_SETTINGS_KEY})
    previous_value = (existing or {}).get("value") if isinstance((existing or {}).get("value"), dict) else None

    await db.admin_settings.update_one(
        {"key": PLANNER_BILLING_SETTINGS_KEY},
        {
            "$set": {
                "key": PLANNER_BILLING_SETTINGS_KEY,
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": now,
            }
        },
        upsert=True,
    )

    await db.admin_settings_history.insert_one(
        {
            "key": PLANNER_BILLING_SETTINGS_KEY,
            "previous_value": previous_value or {"search_profile_click": 1, "planner_intent_click": 0, "qualified_lead": 0, "conversion": 0},
            "new_value": value,
            "changed_by": admin.get("_id"),
            "changed_at": now,
            "change_reason": "billing_pricing_update",
        }
    )

    document = await get_planner_pricing_settings_document(db)
    return {
        "message": "Planner credit values saved",
        "settings": _serialize_pricing_settings(document),
    }


@router.get("/planner-pricing/history")
async def get_planner_pricing_history(
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    rows = []
    cursor = db.admin_settings_history.find({"key": PLANNER_BILLING_SETTINGS_KEY}).sort("changed_at", -1).limit(limit)
    async for row in cursor:
        rows.append(_serialize_pricing_history_entry(row))
    return {"history": rows, "count": len(rows)}


@router.get("/planner-quota")
async def get_planner_quota_settings(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    _ = admin
    document = await get_planner_tourist_quota_settings_document(db)
    return {"settings": _serialize_quota_settings(document)}


@router.post("/planner-quota")
async def save_planner_quota_settings(
    payload: PlannerTouristQuotaSettingsUpdate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    now = datetime.now(timezone.utc)
    value = payload.model_dump()
    existing = await db.admin_settings.find_one({"key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY})
    previous_value = (existing or {}).get("value") if isinstance((existing or {}).get("value"), dict) else None

    await db.admin_settings.update_one(
        {"key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY},
        {
            "$set": {
                "key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY,
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": now,
            }
        },
        upsert=True,
    )

    await db.admin_settings_history.insert_one(
        {
            "key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY,
            "previous_value": previous_value or {
                "daily_limit": 3,
                "monthly_limit": 10,
                "ad_reward_daily_credits": 1,
                "ad_reward_monthly_credits": 1,
                "promotion_reward_daily_credits": 1,
                "promotion_reward_monthly_credits": 2,
            },
            "new_value": value,
            "changed_by": admin.get("_id"),
            "changed_at": now,
            "change_reason": "planner_quota_update",
        }
    )

    document = await get_planner_tourist_quota_settings_document(db)
    return {
        "message": "Planner tourist quota settings saved",
        "settings": _serialize_quota_settings(document),
    }


@router.get("/planner-quota/history")
async def get_planner_quota_history(
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    rows = []
    cursor = db.admin_settings_history.find({"key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY}).sort("changed_at", -1).limit(limit)
    async for row in cursor:
        rows.append(_serialize_pricing_history_entry(row))
    return {"history": rows, "count": len(rows)}


@router.get("/planner-quota/ledger")
async def get_planner_quota_ledger(
    user_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if user_id:
        query["user_id"] = user_id

    rows = []
    cursor = db.tourist_planner_quota_ledger.find(query).sort("created_at", -1).limit(limit)
    async for row in cursor:
        rows.append(await _attach_tourist_identity(db, row))
    return {"entries": rows, "count": len(rows)}


@router.get("/planner-quota/reward-verifications")
async def get_planner_reward_verifications(
    user_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if user_id:
        query["user_id"] = user_id

    rows = []
    cursor = db.tourist_planner_reward_verifications.find(query).sort("created_at", -1).limit(limit)
    async for row in cursor:
        rows.append(await _attach_tourist_identity(db, row))
    return {"records": rows, "count": len(rows)}


@router.get("/summary")
async def get_billing_summary(
    days: int = Query(default=30, ge=1, le=90),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    since = datetime.now(timezone.utc) - timedelta(days=days)

    surface_summary: dict[str, dict] = {}
    async for row in db.billing_event_log.aggregate(
        [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": "$source_surface",
                    "events": {"$sum": 1},
                    "billable_events": {"$sum": {"$cond": ["$is_billable", 1, 0]}},
                    "non_billable_events": {"$sum": {"$cond": ["$is_billable", 0, 1]}},
                    "credits_consumed": {"$sum": "$credits_charged"},
                    "spend_amount": {"$sum": "$currency_amount"},
                }
            },
        ]
    ):
        summary = _empty_surface_summary(row["_id"])
        summary.update(
            {
                "events": row.get("events", 0),
                "billable_events": row.get("billable_events", 0),
                "non_billable_events": row.get("non_billable_events", 0),
                "credits_consumed": row.get("credits_consumed", 0),
                "spend_amount": row.get("spend_amount", 0),
            }
        )
        surface_summary[row["_id"]] = summary

    planner = _empty_planner_summary()
    planner_pricing_document = await get_planner_pricing_settings_document(db)
    planner_quota_document = await get_planner_tourist_quota_settings_document(db)
    planner["pricing"] = planner_pricing_document["values"]
    planner["pricing_source"] = planner_pricing_document["source"]
    planner["pricing_updated_at"] = planner_pricing_document["updated_at"]
    planner["pricing_updated_by"] = planner_pricing_document["updated_by"]
    planner["quota"] = planner_quota_document["values"]
    planner["quota_source"] = planner_quota_document["source"]
    planner["quota_updated_at"] = planner_quota_document["updated_at"]
    planner["quota_updated_by"] = planner_quota_document["updated_by"]
    planner_by_event_type = []
    async for row in db.billing_event_log.aggregate(
        [
            {"$match": {"created_at": {"$gte": since}, "source_surface": "planner"}},
            {
                "$group": {
                    "_id": "$event_type",
                    "events": {"$sum": 1},
                    "billable_events": {"$sum": {"$cond": ["$is_billable", 1, 0]}},
                    "non_billable_events": {"$sum": {"$cond": ["$is_billable", 0, 1]}},
                    "credits_consumed": {"$sum": "$credits_charged"},
                    "spend_amount": {"$sum": "$currency_amount"},
                }
            },
            {"$sort": {"events": -1, "_id": 1}},
        ]
    ):
        item = {
            "event_type": row["_id"],
            "events": row.get("events", 0),
            "billable_events": row.get("billable_events", 0),
            "non_billable_events": row.get("non_billable_events", 0),
            "credits_consumed": row.get("credits_consumed", 0),
            "spend_amount": row.get("spend_amount", 0),
        }
        planner_by_event_type.append(item)
        planner["totals"]["events"] += item["events"]
        planner["totals"]["billable_events"] += item["billable_events"]
        planner["totals"]["non_billable_events"] += item["non_billable_events"]
        planner["totals"]["credits_consumed"] += item["credits_consumed"]
        planner["totals"]["spend_amount"] += item["spend_amount"]

    planner["by_event_type"] = planner_by_event_type
    planner_event_lookup = {item["event_type"]: item["events"] for item in planner_by_event_type}
    served_sessions = await db.billing_event_log.distinct(
        "anonymous_session_id",
        {
            "created_at": {"$gte": since},
            "source_surface": "planner",
            "event_type": "impression",
            "anonymous_session_id": {"$nin": [None, ""]},
        },
    )
    planner["funnel"] = {
        "recommendations_served": len(served_sessions),
        "quote_intents": planner_event_lookup.get("intent_click", 0),
        "itinerary_saves": planner_event_lookup.get("conversion", 0),
    }

    return {
        "days": days,
        "by_surface": [surface_summary[key] for key in sorted(surface_summary.keys())],
        "planner": planner,
    }


@router.post("/adjustments")
async def create_credit_adjustment(
    payload: CreditAdjustmentRequest,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    adjusted = await apply_credit_adjustment(
        db,
        operator_profile_id=payload.operator_profile_id,
        credits_delta=payload.credits_delta,
        notes=payload.notes,
        actor_id=admin.get("_id"),
    )
    return {"message": "Credit adjustment applied", "subscription": _serialize_document(adjusted)}


@router.get("/events")
async def list_billing_events(
    operator_profile_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    query = {}
    if operator_profile_id:
        query["operator_profile_id"] = operator_profile_id
    rows = []
    cursor = db.billing_event_log.find(query).sort("created_at", -1).limit(limit)
    async for row in cursor:
        rows.append(_serialize_document(row))
    return {"events": rows, "count": len(rows)}


@router.get("/reconciliation/credit-events")
async def reconcile_credit_events(
    days: int = Query(default=30, ge=1, le=180),
    limit: int = Query(default=200, ge=1, le=2000),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    since = datetime.now(timezone.utc) - timedelta(days=days)
    report = await build_credit_event_reconciliation_report(db, since=since, limit=limit)

    def _sanitize_issue(issue: dict) -> dict:
        event = _serialize_document(issue.get("event") or {}) if issue.get("event") else None
        ledger = issue.get("ledger")
        if isinstance(ledger, list):
            ledger = [_serialize_document(row) for row in ledger]
        elif isinstance(ledger, dict):
            ledger = _serialize_document(ledger)
        else:
            ledger = None
        return {
            "type": issue.get("type"),
            "operator_profile_id": issue.get("operator_profile_id"),
            "event": event,
            "ledger": ledger,
        }

    issues = [_sanitize_issue(row) for row in report.get("issues", [])]
    orphan_debits = [_serialize_document(row) for row in report.get("orphan_debits", [])]

    return {
        "days": days,
        "limit": limit,
        "billable_events": report.get("billable_events", 0),
        "issue_count": report.get("issue_count", 0),
        "orphan_debit_count": report.get("orphan_debit_count", 0),
        "issues": issues,
        "orphan_debits": orphan_debits,
    }


@router.post("/reconciliation/credit-events/repair")
async def repair_reconciliation_credit_events(
    days: int = Query(default=30, ge=1, le=180),
    limit: int = Query(default=200, ge=1, le=2000),
    max_repairs: int = Query(default=200, ge=1, le=5000),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await repair_credit_event_mismatches(
        db,
        since=since,
        limit=limit,
        max_repairs=max_repairs,
    )
    before = result.get("before") or {}
    after = result.get("after") or {}
    return {
        "message": "Reconciliation repair run completed",
        "days": days,
        "limit": limit,
        "max_repairs": max_repairs,
        "repaired": result.get("repaired", 0),
        "repaired_event_keys": result.get("repaired_event_keys", []),
        "unresolved_missing_debits": result.get("unresolved_missing_debits", 0),
        "unresolved_orphan_debits": result.get("unresolved_orphan_debits", 0),
        "skipped_duplicate_debits": result.get("skipped_duplicate_debits", 0),
        "before": {
            "billable_events": before.get("billable_events", 0),
            "issue_count": before.get("issue_count", 0),
            "orphan_debit_count": before.get("orphan_debit_count", 0),
        },
        "after": {
            "billable_events": after.get("billable_events", 0),
            "issue_count": after.get("issue_count", 0),
            "orphan_debit_count": after.get("orphan_debit_count", 0),
        },
    }


@router.get("/reconciliation/credit-events/anomalies")
async def get_credit_reconciliation_anomalies(
    days: int = Query(default=30, ge=1, le=180),
    limit: int = Query(default=500, ge=1, le=5000),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    since = datetime.now(timezone.utc) - timedelta(days=days)
    counters = await build_credit_anomaly_counters(db, since=since, limit=limit)
    return {
        "days": days,
        "limit": limit,
        "anomalies": counters,
    }


@router.get("/reconciliation/credit-events/export")
async def export_credit_reconciliation_issues(
    days: int = Query(default=30, ge=1, le=180),
    limit: int = Query(default=500, ge=1, le=5000),
    format: str = Query(default="csv"),
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    _ = admin
    since = datetime.now(timezone.utc) - timedelta(days=days)
    report = await build_credit_event_reconciliation_report(db, since=since, limit=limit)

    rows: list[dict] = []
    for issue in report.get("issues", []):
        event = issue.get("event") or {}
        ledger = issue.get("ledger")
        if isinstance(ledger, list):
            ledger_count = len(ledger)
            ledger_credits = ",".join([str((entry or {}).get("credits_delta")) for entry in ledger])
        elif isinstance(ledger, dict):
            ledger_count = 1
            ledger_credits = str(ledger.get("credits_delta"))
        else:
            ledger_count = 0
            ledger_credits = ""

        rows.append(
            {
                "row_type": "issue",
                "issue_type": issue.get("type"),
                "operator_profile_id": issue.get("operator_profile_id") or event.get("operator_profile_id"),
                "event_idempotency_key": event.get("idempotency_key"),
                "event_type": event.get("event_type"),
                "event_credits_charged": event.get("credits_charged"),
                "event_created_at": event.get("created_at"),
                "ledger_count": ledger_count,
                "ledger_credits_delta": ledger_credits,
            }
        )

    for debit in report.get("orphan_debits", []):
        rows.append(
            {
                "row_type": "orphan_debit",
                "issue_type": "orphan_debit",
                "operator_profile_id": debit.get("operator_profile_id"),
                "event_idempotency_key": debit.get("billing_event_idempotency_key"),
                "event_type": None,
                "event_credits_charged": None,
                "event_created_at": None,
                "ledger_count": 1,
                "ledger_credits_delta": debit.get("credits_delta"),
            }
        )

    normalized_format = format.strip().lower()
    if normalized_format == "json":
        return JSONResponse(
            {
                "days": days,
                "limit": limit,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "issue_count": report.get("issue_count", 0),
                    "orphan_debit_count": report.get("orphan_debit_count", 0),
                },
                "rows": rows,
            }
        )

    output = io.StringIO()
    fieldnames = [
        "row_type",
        "issue_type",
        "operator_profile_id",
        "event_idempotency_key",
        "event_type",
        "event_credits_charged",
        "event_created_at",
        "ledger_count",
        "ledger_credits_delta",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    return PlainTextResponse(output.getvalue(), media_type="text/csv")