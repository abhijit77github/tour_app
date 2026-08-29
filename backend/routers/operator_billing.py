import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from ..database import get_database
from ..config import settings
from ..models.billing import OperatorPlanOrderCreateRequest, OperatorPlanSubscribeRequest, PlanOrderPaymentStateUpdateRequest
from ..routers.auth import get_current_operator_access_context
from ..utils.billing import (
    PLAN_ORDER_OPEN_STATUSES,
    apply_refund_credit_compensation,
    apply_webhook_event_to_order,
    create_operator_plan_order,
    ensure_provider_plan,
    should_auto_apply_refund_compensation,
)
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor
from ..utils.payment_provider import (
    build_webhook_idempotency_key,
    create_plan_order_checkout_session,
    extract_webhook_event_details,
    is_payment_refund_event,
    resolve_gateway_status,
    verify_payment_webhook_signature,
)

router = APIRouter(prefix="/operator/billing", tags=["Operator Billing"])
SUPPORTED_PAYMENT_PROVIDERS = ["razorpay", "stripe", "payu"]
OPERATOR_CANCELLABLE_PLAN_ORDER_STATUSES = {"pending_payment", "payment_pending", "payment_received"}


def _serialize_document(doc: dict) -> dict:
    doc = dict(doc)
    if doc.get("_id") is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _extract_signature_header(*, provider: str, x_razorpay_signature: str | None, stripe_signature: str | None, x_payu_signature: str | None) -> str | None:
    provider_key = provider.strip().lower()
    if provider_key == "razorpay":
        return x_razorpay_signature
    if provider_key == "stripe":
        return stripe_signature
    if provider_key == "payu":
        return x_payu_signature
    return None


@router.get("/plan")
async def get_operator_billing_plan(access_context: dict = Depends(get_current_operator_access_context)):
    db = await get_database()
    profile = access_context["operator_profile"]
    subscription = await ensure_provider_plan(
        db,
        operator_profile_id=str(profile["_id"]),
        operator_user_id=str(access_context["principal"]["_id"]),
    )
    plan_doc = await db.billing_plans.find_one({"code": subscription["plan_code"]})
    requested_plan_doc = None
    if subscription.get("requested_plan_code"):
        requested_plan_doc = await db.billing_plans.find_one({"code": subscription["requested_plan_code"]})
    open_plan_order = await db.plan_orders.find_one(
        {
            "operator_profile_id": str(profile["_id"]),
            "order_status": {"$in": list(PLAN_ORDER_OPEN_STATUSES)},
        },
        sort=[("created_at", -1)],
    )
    active_promotions = await db.location_promotions.count_documents(
        {"operator_profile_id": str(profile["_id"]), "status": "active"}
    )
    return {
        "subscription": _serialize_document(subscription),
        "plan": _serialize_document(plan_doc) if plan_doc else None,
        "requested_plan": _serialize_document(requested_plan_doc) if requested_plan_doc else None,
        "open_plan_order": _serialize_document(open_plan_order) if open_plan_order else None,
        "active_promotions": active_promotions,
    }


@router.get("/plans")
async def list_operator_billing_plans(access_context: dict = Depends(get_current_operator_access_context)):
    db = await get_database()
    _ = access_context

    plans = []
    cursor = db.billing_plans.find({"is_active": True}).sort([("monthly_price", 1), ("code", 1)])
    async for plan in cursor:
        plans.append(_serialize_document(plan))
    return {
        "plans": plans,
        "count": len(plans),
        "payment_providers": SUPPORTED_PAYMENT_PROVIDERS,
        "gateway_status": "not_configured",
        "message": "Plan orders are created and tracked now; gateway checkout/session attachment plugs in later.",
    }


@router.get("/orders")
async def list_operator_plan_orders(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    base_query = {"operator_profile_id": str(profile["_id"])}
    total_items = await db.plan_orders.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]
    rows = []
    docs = await db.plan_orders.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(docs) > page_size
    docs = docs[:page_size]
    next_cursor = None
    if has_more and docs:
        last_row = docs[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])
    for row in docs:
        rows.append(_serialize_document(row))
    return {
        "orders": rows,
        "count": len(rows),
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_operator_billing_order(
    payload: OperatorPlanOrderCreateRequest,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]

    plan_doc = await db.billing_plans.find_one({"code": payload.plan_code, "is_active": True})
    if not plan_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing plan not found")

    try:
        order, created = await create_operator_plan_order(
            db,
            operator_profile_id=str(profile["_id"]),
            operator_user_id=str(access_context["principal"]["_id"]),
            organization_id=str(access_context["organization"]["_id"]),
            plan_doc=plan_doc,
            payment_provider=payload.payment_provider,
            client_request_id=payload.client_request_id,
        )
    except ValueError as exc:
        if str(exc) == "free_plan_not_orderable":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Free plan does not require a purchase order") from exc
        if str(exc) == "open_order_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an open plan purchase order. Complete or cancel it before creating another.") from exc
        raise

    checkout_payload = await create_plan_order_checkout_session(
        payment_provider=payload.payment_provider,
        order_code=order.get("order_code", ""),
        amount=float(order.get("amount") or 0),
        currency=str(order.get("currency") or "INR"),
    )
    if created and (checkout_payload.get("gateway_session_id") or checkout_payload.get("gateway_order_id")):
        now = datetime.now(timezone.utc)
        update_fields = {
            "updated_at": now,
        }
        if checkout_payload.get("gateway_session_id"):
            update_fields["gateway_session_id"] = checkout_payload.get("gateway_session_id")
        if checkout_payload.get("gateway_order_id"):
            update_fields["gateway_order_id"] = checkout_payload.get("gateway_order_id")
        if order.get("payment_status") == "not_started":
            update_fields["payment_status"] = "pending"
        if order.get("order_status") == "pending_payment":
            update_fields["order_status"] = "payment_pending"

        await db.plan_orders.update_one(
            {"_id": order["_id"]},
            {
                "$set": update_fields,
                "$push": {
                    "status_history": {
                        "timestamp": now,
                        "order_status": update_fields.get("order_status", order.get("order_status")),
                        "payment_status": update_fields.get("payment_status", order.get("payment_status")),
                        "fulfillment_status": order.get("fulfillment_status", "not_started"),
                        "actor_id": str(access_context["principal"]["_id"]),
                        "note": "Attached provider checkout/session references",
                        "metadata": {
                            "gateway_session_id": checkout_payload.get("gateway_session_id"),
                            "gateway_order_id": checkout_payload.get("gateway_order_id"),
                            "payment_provider": payload.payment_provider,
                        },
                    }
                },
            },
        )
        order = await db.plan_orders.find_one({"_id": order["_id"]})

    return {
        "message": "Plan order created. Attach the payment gateway checkout session in the next integration step." if created else "Existing plan order reused for this client request.",
        "order": _serialize_document(order),
        "gateway_status": resolve_gateway_status(checkout_payload=checkout_payload),
        "checkout": checkout_payload,
        "next_action": "Create or attach a provider checkout/order session, then settle the order after payment verification.",
        "created": created,
    }


@router.patch("/orders/{order_id}/payment-state")
async def update_operator_plan_order_payment_state(
    order_id: str,
    payload: PlanOrderPaymentStateUpdateRequest,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    try:
        order = await db.plan_orders.find_one({"_id": ObjectId(order_id), "operator_profile_id": str(profile["_id"])})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id") from exc

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan order not found")
    if order.get("order_status") not in PLAN_ORDER_OPEN_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment references can only be updated for open plan orders")

    update_fields = {"updated_at": datetime.now(timezone.utc)}
    if payload.gateway_session_id is not None:
        update_fields["gateway_session_id"] = payload.gateway_session_id
    if payload.gateway_order_id is not None:
        update_fields["gateway_order_id"] = payload.gateway_order_id
    if payload.payment_reference is not None:
        update_fields["payment_reference"] = payload.payment_reference
    if payload.gateway_metadata:
        update_fields["gateway_metadata"] = payload.gateway_metadata

    has_state_updates = len(update_fields) > 1
    if not has_state_updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No payment state fields provided")

    if order.get("payment_status") == "not_started" and (
        payload.gateway_session_id is not None or payload.gateway_order_id is not None
    ):
        update_fields["payment_status"] = "pending"
        if order.get("order_status") == "pending_payment":
            update_fields["order_status"] = "payment_pending"

    next_order_status = update_fields.get("order_status", order.get("order_status"))
    next_payment_status = update_fields.get("payment_status", order.get("payment_status"))
    next_fulfillment_status = order.get("fulfillment_status", "not_started")

    result = await db.plan_orders.update_one(
        {"_id": order["_id"], "order_status": {"$in": list(PLAN_ORDER_OPEN_STATUSES)}},
        {
            "$set": update_fields,
            "$push": {
                "status_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "order_status": next_order_status,
                    "payment_status": next_payment_status,
                    "fulfillment_status": next_fulfillment_status,
                    "actor_id": str(access_context["principal"]["_id"]),
                    "note": "Operator updated payment references",
                    "metadata": {
                        "gateway_session_id": payload.gateway_session_id,
                        "gateway_order_id": payload.gateway_order_id,
                        "payment_reference": payload.payment_reference,
                    },
                }
            },
        },
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan order state changed before payment update. Refresh and retry.")

    updated = await db.plan_orders.find_one({"_id": order["_id"]})
    return {
        "message": "Plan order payment references updated",
        "order": _serialize_document(updated),
    }


@router.post("/webhooks/{provider}")
async def handle_operator_billing_webhook(
    provider: str,
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    stripe_signature: str | None = Header(default=None),
    x_payu_signature: str | None = Header(default=None),
):
    provider_key = provider.strip().lower()
    if provider_key not in set(SUPPORTED_PAYMENT_PROVIDERS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported payment provider")

    payload_bytes = await request.body()
    signature = _extract_signature_header(
        provider=provider_key,
        x_razorpay_signature=x_razorpay_signature,
        stripe_signature=stripe_signature,
        x_payu_signature=x_payu_signature,
    )
    verified, reason = verify_payment_webhook_signature(provider=provider_key, payload=payload_bytes, signature=signature)
    if not verified:
        if reason == "webhook_secret_not_configured":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook secret not configured")
        if reason == "unsupported_provider":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported payment provider")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc

    details = extract_webhook_event_details(provider=provider_key, payload=payload)
    idempotency_key = build_webhook_idempotency_key(
        provider=provider_key,
        event_id=str(details["event_id"]),
        payload=payload_bytes,
    )

    db = await get_database()
    now = datetime.now(timezone.utc)
    insert_result = await db.billing_webhook_events.update_one(
        {"idempotency_key": idempotency_key},
        {
            "$setOnInsert": {
                "idempotency_key": idempotency_key,
                "provider": provider_key,
                "event_id": details.get("event_id"),
                "event_type": details.get("event_type"),
                "payload": payload,
                "gateway_order_id": details.get("gateway_order_id"),
                "gateway_payment_id": details.get("gateway_payment_id"),
                "payment_reference": details.get("payment_reference"),
                "order_code": details.get("order_code"),
                "processed": False,
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
    )

    is_new_event = bool(getattr(insert_result, "upserted_id", None))
    if not is_new_event:
        return {"ok": True, "duplicate": True, "processed": True}

    order = None
    if details.get("order_code"):
        order = await db.plan_orders.find_one({"order_code": details["order_code"]})
    if not order and details.get("gateway_order_id"):
        order = await db.plan_orders.find_one({"gateway_order_id": details["gateway_order_id"]})

    order_update_applied = False
    refund_compensation = None
    is_refund_event = is_payment_refund_event(provider=provider_key, event_type=str(details.get("event_type") or ""))
    if order:
        order_update_applied = await apply_webhook_event_to_order(
            db,
            order=order,
            provider=provider_key,
            event_id=details.get("event_id"),
            event_type=str(details.get("event_type") or ""),
            payment_reference=details.get("payment_reference"),
            gateway_payment_id=details.get("gateway_payment_id"),
            gateway_order_id=details.get("gateway_order_id"),
            actor_id="system:webhook",
        )
        if is_refund_event and should_auto_apply_refund_compensation():
            refreshed_order = await db.plan_orders.find_one({"_id": order["_id"]})
            if refreshed_order:
                try:
                    refund_compensation = await apply_refund_credit_compensation(
                        db,
                        order=refreshed_order,
                        actor_id="system:webhook",
                        notes="Auto compensation triggered by refund webhook",
                    )
                except ValueError as exc:
                    refund_compensation = {
                        "applied": False,
                        "reason": str(exc),
                    }

    await db.billing_webhook_events.update_one(
        {"idempotency_key": idempotency_key},
        {
            "$set": {
                "processed": True,
                "processed_at": now,
                "order_found": bool(order),
                "order_update_applied": order_update_applied,
                "refund_compensation_mode": str(settings.billing_refund_compensation_mode or "manual"),
                "refund_compensation_result": refund_compensation,
                "updated_at": now,
            }
        },
    )

    return {
        "ok": True,
        "duplicate": False,
        "processed": True,
        "order_found": bool(order),
        "order_update_applied": order_update_applied,
        "refund_compensation": refund_compensation,
    }


@router.delete("/orders/{order_id}")
async def cancel_operator_billing_order(
    order_id: str,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    try:
        order = await db.plan_orders.find_one({"_id": ObjectId(order_id), "operator_profile_id": str(profile["_id"])})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id") from exc

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan order not found")
    if order.get("order_status") not in OPERATOR_CANCELLABLE_PLAN_ORDER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only unpaid or unfulfilled plan orders can be cancelled here")

    result = await db.plan_orders.update_one(
        {"_id": order["_id"], "order_status": {"$in": list(OPERATOR_CANCELLABLE_PLAN_ORDER_STATUSES)}},
        {
            "$set": {
                "order_status": "cancelled",
                "payment_status": "cancelled",
                "fulfillment_status": "not_started",
                "cancelled_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            "$push": {
                "status_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "order_status": "cancelled",
                    "payment_status": "cancelled",
                    "fulfillment_status": "not_started",
                    "actor_id": str(access_context["principal"]["_id"]),
                    "note": "Operator cancelled plan order before settlement",
                    "metadata": {},
                }
            },
        },
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Plan order state changed before cancellation. Refresh and retry.",
        )
    return {"message": "Plan order cancelled successfully"}


@router.post("/subscribe")
async def request_operator_plan_change(
    payload: OperatorPlanSubscribeRequest,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]

    plan_doc = await db.billing_plans.find_one({"code": payload.plan_code, "is_active": True})
    if not plan_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing plan not found")

    if payload.plan_code == "FREE":
        subscription = await ensure_provider_plan(
            db,
            operator_profile_id=str(profile["_id"]),
            operator_user_id=str(access_context["principal"]["_id"]),
        )
        return {
            "message": "Free plan remains active",
            "subscription": _serialize_document(subscription),
        }

    try:
        order, created = await create_operator_plan_order(
            db,
            operator_profile_id=str(profile["_id"]),
            operator_user_id=str(access_context["principal"]["_id"]),
            organization_id=str(access_context["organization"]["_id"]),
            plan_doc=plan_doc,
            payment_provider="razorpay",
            client_request_id=f"legacy-{uuid4().hex}",
        )
    except ValueError as exc:
        if str(exc) == "open_order_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an open plan purchase order. Complete or cancel it before creating another.") from exc
        raise
    return {
        "message": "Deprecated subscribe flow redirected to plan order creation. Complete payment integration against /operator/billing/orders.",
        "order": _serialize_document(order),
        "created": created,
    }


@router.get("/ledger")
async def get_operator_credit_ledger(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    await ensure_provider_plan(
        db,
        operator_profile_id=str(profile["_id"]),
        operator_user_id=str(access_context["principal"]["_id"]),
    )

    base_query = {"operator_profile_id": str(profile["_id"])}
    total_items = await db.credit_ledger.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]

    rows = []
    docs = await db.credit_ledger.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(docs) > page_size
    docs = docs[:page_size]
    next_cursor = None
    if has_more and docs:
        last_row = docs[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])
    for row in docs:
        rows.append(_serialize_document(row))

    return {
        "entries": rows,
        "count": len(rows),
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.get("/analytics")
async def get_operator_billing_analytics(
    days: int = Query(default=30, ge=1, le=90),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    await ensure_provider_plan(
        db,
        operator_profile_id=str(profile["_id"]),
        operator_user_id=str(access_context["principal"]["_id"]),
    )
    operator_profile_id = str(profile["_id"])
    since = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {
            "$match": {
                "operator_profile_id": operator_profile_id,
                "created_at": {"$gte": since},
            }
        },
        {
            "$group": {
                "_id": "$source_surface",
                "billable_events": {"$sum": {"$cond": ["$is_billable", 1, 0]}},
                "non_billable_events": {"$sum": {"$cond": ["$is_billable", 0, 1]}},
                "credits_consumed": {"$sum": "$credits_charged"},
                "spend_amount": {"$sum": "$currency_amount"},
            }
        },
    ]
    by_surface_cursor = db.billing_event_log.aggregate(pipeline)
    by_surface = []
    async for row in by_surface_cursor:
        by_surface.append(
            {
                "surface": row["_id"],
                "billable_events": row.get("billable_events", 0),
                "non_billable_events": row.get("non_billable_events", 0),
                "credits_consumed": row.get("credits_consumed", 0),
                "spend_amount": row.get("spend_amount", 0),
            }
        )

    daily_pipeline = [
        {
            "$match": {
                "operator_profile_id": operator_profile_id,
                "created_at": {"$gte": since},
                "is_billable": True,
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "surface": "$source_surface",
                },
                "credits_consumed": {"$sum": "$credits_charged"},
                "spend_amount": {"$sum": "$currency_amount"},
                "events": {"$sum": 1},
            }
        },
        {"$sort": {"_id.date": 1}},
    ]
    daily_rows = []
    async for row in db.billing_event_log.aggregate(daily_pipeline):
        daily_rows.append(
            {
                "date": row["_id"]["date"],
                "surface": row["_id"]["surface"],
                "events": row.get("events", 0),
                "credits_consumed": row.get("credits_consumed", 0),
                "spend_amount": row.get("spend_amount", 0),
            }
        )

    totals = {
        "billable_events": sum(item["billable_events"] for item in by_surface),
        "non_billable_events": sum(item["non_billable_events"] for item in by_surface),
        "credits_consumed": sum(item["credits_consumed"] for item in by_surface),
        "spend_amount": sum(item["spend_amount"] for item in by_surface),
    }

    return {
        "days": days,
        "totals": totals,
        "by_surface": by_surface,
        "daily": daily_rows,
    }