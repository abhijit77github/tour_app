from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_database
from ..models.promotion import PromotionLocationScope
from ..models.promotion_package import PromotionPurchaseRequest
from ..routers.auth import get_current_operator_access_context
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor

router = APIRouter(prefix="/operator/promotions", tags=["Operator Promotions"])


def _normalize_location_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.casefold() if cleaned else None


def _build_normalized_scope(scope: dict) -> dict:
    return {
        "area_name": _normalize_location_value(scope.get("area_name")),
        "state": _normalize_location_value(scope.get("state")),
        "country": _normalize_location_value(scope.get("country")),
    }


def _scope_matches_area(scope: dict, area: dict) -> bool:
    if scope.get("area_name") and _normalize_location_value(area.get("area_name")) != _normalize_location_value(scope.get("area_name")):
        return False
    if scope.get("state") and _normalize_location_value(area.get("state")) != _normalize_location_value(scope.get("state")):
        return False
    if scope.get("country") and _normalize_location_value(area.get("country")) != _normalize_location_value(scope.get("country")):
        return False
    return True


def _serialize_package(package: dict) -> dict:
    package["_id"] = str(package["_id"])
    return package


def _serialize_order(order: dict) -> dict:
    order["_id"] = str(order["_id"])
    return order


@router.get("/packages")
async def list_promotion_packages(
    limit: int = Query(default=50, ge=1, le=100),
    access_context: dict = Depends(get_current_operator_access_context),
):
    """List active promotion packages available to operators."""
    db = await get_database()
    _ = access_context

    packages = []
    cursor = db.promotion_packages.find({"is_active": True}).sort([("price", 1), ("priority", 1)]).limit(limit)
    async for package in cursor:
        packages.append(_serialize_package(package))

    return {
        "packages": packages,
        "payment_providers": ["razorpay", "stripe", "payu"],
        "gateway_status": "not_configured",
        "message": "Payment gateway session creation will plug into this flow later.",
    }


@router.get("/orders")
async def list_my_promotion_orders(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    access_context: dict = Depends(get_current_operator_access_context),
):
    """List promotion purchase orders created by the current operator."""
    db = await get_database()
    profile = access_context["operator_profile"]

    base_query = {"operator_profile_id": str(profile["_id"])}
    total_items = await db.promotion_orders.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]

    orders = []
    rows = await db.promotion_orders.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])
    for order in rows:
        orders.append(_serialize_order(order))

    return {
        "orders": orders,
        "count": len(orders),
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.post("/purchase", status_code=status.HTTP_201_CREATED)
async def create_promotion_purchase(
    purchase: PromotionPurchaseRequest,
    access_context: dict = Depends(get_current_operator_access_context),
):
    """Create a promotion purchase order for later gateway checkout."""
    db = await get_database()
    profile = access_context["operator_profile"]

    try:
        package = await db.promotion_packages.find_one({"_id": ObjectId(purchase.package_id), "is_active": True})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package_id") from exc

    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion package not found")

    if purchase.service_type not in package.get("available_service_types", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected package does not support this service type",
        )

    if purchase.service_type not in profile.get("service_types", ["tour"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your operator profile does not support this service type",
        )

    location_scope = purchase.location_scope.model_dump()
    if not any(_scope_matches_area(location_scope, area) for area in profile.get("serving_areas", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected location is not part of your serving areas",
        )

    now = datetime.now(timezone.utc)
    package_snapshot = {
        "code": package["code"],
        "name": package["name"],
        "duration_days": package["duration_days"],
        "priority": package["priority"],
        "promotion_label": package.get("promotion_label", "Promoted"),
        "price": float(package["price"]),
        "currency": package.get("currency", "INR"),
        "requires_admin_approval": package.get("requires_admin_approval", True),
        "features": package.get("features", []),
    }

    order_doc = {
        "operator_profile_id": str(profile["_id"]),
        "operator_user_id": str(access_context["principal"]["_id"]),
        "organization_id": access_context["organization"]["_id"],
        "package_id": str(package["_id"]),
        "package_snapshot": package_snapshot,
        "location_scope": location_scope,
        "normalized_location_scope": _build_normalized_scope(location_scope),
        "service_type": purchase.service_type,
        "payment_provider": purchase.payment_provider,
        "amount": float(package["price"]),
        "currency": package.get("currency", "INR"),
        "order_status": "pending_payment",
        "payment_status": "not_started",
        "payment_reference": None,
        "gateway_session_id": None,
        "campaign_status": "awaiting_payment",
        "created_at": now,
        "updated_at": now,
        "planned_start_at": now,
        "planned_end_at": now + timedelta(days=int(package["duration_days"])),
    }

    result = await db.promotion_orders.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id

    return {
        "message": "Promotion purchase order created. Attach Razorpay, Stripe, or PayU checkout in the next step.",
        "order": _serialize_order(order_doc),
        "gateway_status": "not_configured",
        "next_action": "Create a payment intent/session for the selected provider, then confirm payment via webhook before activating the campaign.",
    }


@router.delete("/orders/{order_id}")
async def cancel_promotion_order(
    order_id: str,
    access_context: dict = Depends(get_current_operator_access_context),
):
    """Cancel a pending promotion purchase order."""
    db = await get_database()
    profile = access_context["operator_profile"]

    try:
        order = await db.promotion_orders.find_one({"_id": ObjectId(order_id), "operator_profile_id": str(profile["_id"])})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id") from exc

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion order not found")

    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid orders cannot be cancelled here")

    await db.promotion_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"order_status": "cancelled", "payment_status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
    )

    return {"message": "Promotion order cancelled successfully"}