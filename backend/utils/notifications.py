from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, status

from .cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor


NOTIFICATION_TYPE_LABELS = {
    "notification": "Notification",
    "announcement": "Announcement",
    "alert": "Alert",
}

NOTIFICATION_STATUS_LABELS = {
    "draft": "Draft",
    "scheduled": "Scheduled",
    "processing": "Processing",
    "sent": "Sent",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

ADMIN_ALERT_SEVERITY_LABELS = {
    "info": "Info",
    "warning": "Warning",
    "error": "Error",
}

DEFAULT_NOTIFICATION_PREFERENCES = {
    "in_app_enabled": True,
    "marketing_enabled": True,
    "announcements_enabled": True,
    "alerts_enabled": True,
    "quiet_hours_enabled": False,
    "quiet_hours_start": None,
    "quiet_hours_end": None,
    "timezone": "UTC",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def _to_object_id(value: str, *, detail: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


def _normalize_recipient_filter(payload: dict | None) -> dict:
    data = deepcopy(payload or {})
    normalized = {
        "active_only": bool(data.get("active_only", False)),
        "last_active_days": data.get("last_active_days"),
    }
    if normalized["last_active_days"] is not None:
        normalized["last_active_days"] = int(normalized["last_active_days"])
    return normalized


def _user_last_activity(user: dict):
    return user.get("last_login") or user.get("updated_at") or user.get("created_at")


def _resolve_timezone(value: str | None):
    try:
        return ZoneInfo(value or "UTC")
    except Exception:
        return timezone.utc


def _clock_to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _is_in_quiet_hours(preferences: dict, *, now: datetime) -> bool:
    if not preferences.get("quiet_hours_enabled"):
        return False
    start_minutes = _clock_to_minutes(preferences.get("quiet_hours_start"))
    end_minutes = _clock_to_minutes(preferences.get("quiet_hours_end"))
    if start_minutes is None or end_minutes is None:
        return False

    localized_now = now.astimezone(_resolve_timezone(preferences.get("timezone")))
    current_minutes = localized_now.hour * 60 + localized_now.minute

    if start_minutes == end_minutes:
        return False
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _matches_recipient(user: dict, recipient_type: str, recipient_filter: dict, *, now: datetime) -> bool:
    user_type = user.get("user_type")
    if recipient_type == "tourists" and user_type != "tourist":
        return False
    if recipient_type == "operators" and user_type != "operator":
        return False
    if recipient_type == "all" and user_type not in {"tourist", "operator"}:
        return False

    if recipient_filter.get("active_only") and user.get("is_active") is False:
        return False

    window_days = recipient_filter.get("last_active_days")
    if window_days:
        last_activity = _user_last_activity(user)
        if not isinstance(last_activity, datetime):
            return False
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        if last_activity < now - timedelta(days=int(window_days)):
            return False

    return True


def _build_notification_recipient_pipeline(recipient_type: str, recipient_filter: dict, *, now: datetime) -> list[dict]:
    user_types = {
        "tourists": ["tourist"],
        "operators": ["operator"],
        "all": ["tourist", "operator"],
    }.get(recipient_type, [])

    pipeline: list[dict] = []
    if user_types:
        pipeline.append({"$match": {"user_type": {"$in": user_types}}})

    if recipient_filter.get("active_only"):
        pipeline.append({"$match": {"is_active": {"$ne": False}}})

    window_days = recipient_filter.get("last_active_days")
    if window_days:
        cutoff = now - timedelta(days=int(window_days))
        pipeline.extend(
            [
                {
                    "$addFields": {
                        "_last_activity": {
                            "$ifNull": [
                                "$last_login",
                                {"$ifNull": ["$updated_at", "$created_at"]},
                            ]
                        }
                    }
                },
                {"$match": {"_last_activity": {"$gte": cutoff}}},
            ]
        )

    return pipeline


async def list_matching_notification_recipients(db, *, recipient_type: str, recipient_filter: dict | None = None, now: datetime | None = None) -> list[dict]:
    now = now or _utcnow()
    normalized_filter = _normalize_recipient_filter(recipient_filter)
    pipeline = _build_notification_recipient_pipeline(recipient_type, normalized_filter, now=now)
    users = await db.users.aggregate(pipeline).to_list(length=None)
    return [
        {key: value for key, value in user.items() if key != "_last_activity"}
        for user in users
        if _matches_recipient(user, recipient_type, normalized_filter, now=now)
    ]


async def preview_notification_audience(db, *, recipient_type: str, recipient_filter: dict | None = None, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    normalized_filter = _normalize_recipient_filter(recipient_filter)
    pipeline = _build_notification_recipient_pipeline(recipient_type, normalized_filter, now=now)
    pipeline.append(
        {
            "$group": {
                "_id": "$user_type",
                "count": {"$sum": 1},
            }
        }
    )
    counts = await db.users.aggregate(pipeline).to_list(length=None)
    breakdown = {
        "tourists": 0,
        "operators": 0,
    }
    for row in counts:
        if row.get("_id") == "tourist":
            breakdown["tourists"] = row.get("count", 0)
        elif row.get("_id") == "operator":
            breakdown["operators"] = row.get("count", 0)

    return {
        "recipient_type": recipient_type,
        "recipient_filter": normalized_filter,
        "estimated_recipients": breakdown["tourists"] + breakdown["operators"],
        "breakdown": breakdown,
        "as_of": _serialize_datetime(now),
    }


def serialize_notification_template(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "name": document.get("name"),
        "category": document.get("category"),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "channels": document.get("channels", ["in_app"]),
        "is_active": bool(document.get("is_active", True)),
        "created_at": _serialize_datetime(document.get("created_at")),
        "updated_at": _serialize_datetime(document.get("updated_at")),
        "created_by": document.get("created_by"),
        "updated_by": document.get("updated_by"),
    }


def serialize_notification_campaign(document: dict) -> dict:
    campaign_type = document.get("type", "notification")
    status_value = document.get("status", "draft")
    return {
        "_id": str(document.get("_id")),
        "type": campaign_type,
        "type_label": NOTIFICATION_TYPE_LABELS.get(campaign_type, campaign_type.title()),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "channel": document.get("channel", "in_app"),
        "recipient_type": document.get("recipient_type"),
        "recipient_filter": document.get("recipient_filter", {}),
        "recipient_count": int(document.get("recipient_count", 0) or 0),
        "status": status_value,
        "status_label": NOTIFICATION_STATUS_LABELS.get(status_value, status_value.title()),
        "scheduled_for": _serialize_datetime(document.get("scheduled_for")),
        "sent_at": _serialize_datetime(document.get("sent_at")),
        "created_at": _serialize_datetime(document.get("created_at")),
        "updated_at": _serialize_datetime(document.get("updated_at")),
        "template_id": document.get("template_id"),
        "delivery_stats": document.get("delivery_stats", {}),
        "metadata": document.get("metadata", {}),
        "created_by": document.get("created_by"),
        "updated_by": document.get("updated_by"),
        "last_worker_run_at": _serialize_datetime(document.get("last_worker_run_at")),
        "failure_reason": document.get("failure_reason"),
    }


def serialize_admin_alert(document: dict) -> dict:
    severity = document.get("severity", "info")
    return {
        "_id": str(document.get("_id")),
        "title": document.get("title"),
        "message": document.get("message"),
        "severity": severity,
        "severity_label": ADMIN_ALERT_SEVERITY_LABELS.get(severity, severity.title()),
        "category": document.get("category", "notification"),
        "service": document.get("service", "notification"),
        "read": bool(document.get("read", False)),
        "created_at": _serialize_datetime(document.get("created_at")),
        "read_at": _serialize_datetime(document.get("read_at")),
        "source_reference_type": document.get("source_reference_type"),
        "source_reference_id": document.get("source_reference_id"),
        "metadata": document.get("metadata", {}),
    }


def serialize_notification_delivery(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "campaign_id": document.get("campaign_id"),
        "user_id": document.get("user_id"),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "type": document.get("type"),
        "type_label": NOTIFICATION_TYPE_LABELS.get(document.get("type", "notification"), document.get("type", "notification").title()),
        "channel": document.get("channel", "in_app"),
        "status": document.get("status", "delivered"),
        "created_at": _serialize_datetime(document.get("created_at")),
        "delivered_at": _serialize_datetime(document.get("delivered_at")),
        "read_at": _serialize_datetime(document.get("read_at")),
        "metadata": document.get("metadata", {}),
        "suppression_reason": document.get("suppression_reason"),
    }


def serialize_worker_run(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "worker_id": document.get("worker_id"),
        "started_at": _serialize_datetime(document.get("started_at")),
        "finished_at": _serialize_datetime(document.get("finished_at")),
        "claimed_campaigns": int(document.get("claimed_campaigns", 0) or 0),
        "processed_campaigns": int(document.get("processed_campaigns", 0) or 0),
        "failed_campaigns": int(document.get("failed_campaigns", 0) or 0),
        "delivery_attempts": int(document.get("delivery_attempts", 0) or 0),
        "status": document.get("status", "idle"),
        "last_error": document.get("last_error"),
        "metadata": document.get("metadata", {}),
    }


def serialize_notification_preferences(document: dict) -> dict:
    values = {**DEFAULT_NOTIFICATION_PREFERENCES, **(document.get("preferences") or document)}
    return {
        "user_id": document.get("user_id"),
        "preferences": values,
        "updated_at": _serialize_datetime(document.get("updated_at")),
    }


async def append_notification_audit_log(db, *, entity_type: str, entity_id: str, action: str, admin: dict, metadata: dict | None = None, created_at: datetime | None = None):
    created_at = created_at or _utcnow()
    await db.notification_audit_log.insert_one(
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_id": admin.get("_id"),
            "actor_name": admin.get("full_name") or admin.get("email") or "Admin",
            "created_at": created_at,
            "metadata": metadata or {},
        }
    )


async def append_admin_alert(
    db,
    *,
    title: str,
    message: str,
    severity: str = "info",
    category: str = "notification",
    source_reference_type: str | None = None,
    source_reference_id: str | None = None,
    metadata: dict | None = None,
    created_at: datetime | None = None,
):
    created_at = created_at or _utcnow()
    await db.admin_alerts.insert_one(
        {
            "title": title,
            "message": message,
            "severity": severity,
            "category": category,
            "service": "notification",
            "read": False,
            "created_at": created_at,
            "read_at": None,
            "source_reference_type": source_reference_type,
            "source_reference_id": source_reference_id,
            "metadata": metadata or {},
        }
    )


async def list_admin_alerts(db, *, unread_only: bool = False, limit: int = 50) -> list[dict]:
    alerts = await db.admin_alerts.find({}).to_list(length=max(limit, 200))
    if unread_only:
        alerts = [item for item in alerts if not item.get("read")]
    alerts.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_admin_alert(item) for item in alerts[:limit]]


async def mark_admin_alert_as_read(db, alert_id: str, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(alert_id, detail="Invalid alert_id")
    existing = await db.admin_alerts.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin alert not found")
    await db.admin_alerts.update_one({"_id": object_id}, {"$set": {"read": True, "read_at": now}})
    existing.update({"read": True, "read_at": now})
    return serialize_admin_alert(existing)


async def mark_all_admin_alerts_as_read(db, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    await db.admin_alerts.update_many({"read": False}, {"$set": {"read": True, "read_at": now}})
    unread = await list_admin_alerts(db, unread_only=True, limit=1)
    return {"unread_count": len(unread)}


async def list_notification_templates(db) -> list[dict]:
    templates = await db.notification_templates.find({}).to_list(length=200)
    templates.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_notification_template(item) for item in templates]


async def create_notification_template(db, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    document = {
        "name": payload["name"],
        "category": payload["category"],
        "subject": payload["subject"],
        "message": payload["message"],
        "channels": payload.get("channels", ["in_app"]),
        "is_active": bool(payload.get("is_active", True)),
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
    }
    result = await db.notification_templates.insert_one(document)
    document["_id"] = result.inserted_id
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=str(result.inserted_id),
        action="created",
        admin=admin,
        metadata={"name": document["name"]},
        created_at=now,
    )
    return serialize_notification_template(document)


async def update_notification_template(db, template_id: str, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(template_id, detail="Invalid template_id")
    existing = await db.notification_templates.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")

    updates = {
        **payload,
        "updated_at": now,
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
    }
    await db.notification_templates.update_one({"_id": object_id}, {"$set": updates})
    existing.update(updates)
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=template_id,
        action="updated",
        admin=admin,
        metadata={"updated_fields": sorted(payload.keys())},
        created_at=now,
    )
    return serialize_notification_template(existing)


async def delete_notification_template(db, template_id: str, *, admin: dict, now: datetime | None = None) -> None:
    now = now or _utcnow()
    object_id = _to_object_id(template_id, detail="Invalid template_id")
    existing = await db.notification_templates.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")

    linked_campaign = await db.notification_campaigns.find_one({"template_id": template_id})
    if linked_campaign:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is already referenced by an existing campaign",
        )

    await db.notification_templates.delete_one({"_id": object_id})
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=template_id,
        action="deleted",
        admin=admin,
        metadata={"name": existing.get("name")},
        created_at=now,
    )


async def list_notification_campaigns(db, *, campaign_type: str | None = None, status_value: str | None = None) -> list[dict]:
    campaigns = await db.notification_campaigns.find({}).to_list(length=300)
    if campaign_type:
        campaigns = [item for item in campaigns if item.get("type") == campaign_type]
    if status_value:
        campaigns = [item for item in campaigns if item.get("status") == status_value]
    campaigns.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_notification_campaign(item) for item in campaigns]


async def get_notification_campaign(db, campaign_id: str) -> dict:
    object_id = _to_object_id(campaign_id, detail="Invalid campaign_id")
    campaign = await db.notification_campaigns.find_one({"_id": object_id})
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification campaign not found")
    return serialize_notification_campaign(campaign)


async def create_notification_campaign(db, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    audience = await preview_notification_audience(
        db,
        recipient_type=payload["recipient_type"],
        recipient_filter=payload.get("recipient_filter"),
        now=now,
    )

    scheduled_for = payload.get("scheduled_for")
    if scheduled_for and scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    if not payload.get("send_now"):
        if scheduled_for is None or scheduled_for <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scheduled_for must be in the future")

    initial_status = "processing" if payload.get("send_now", True) else "scheduled"
    document = {
        "type": payload.get("type", "notification"),
        "subject": payload["subject"],
        "message": payload["message"],
        "channel": payload.get("channel", "in_app"),
        "recipient_type": payload["recipient_type"],
        "recipient_filter": audience["recipient_filter"],
        "recipient_count": audience["estimated_recipients"],
        "status": initial_status,
        "scheduled_for": scheduled_for,
        "sent_at": None,
        "created_at": now,
        "updated_at": now,
        "template_id": payload.get("template_id"),
        "metadata": payload.get("metadata", {}),
        "created_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "delivery_stats": {
            "accepted": 0,
            "delivered": 0,
            "opened": 0,
            "clicked": 0,
            "failed": 0,
            "suppressed": 0,
            "read": 0,
        },
        "failure_reason": None,
        "worker_lock_id": None,
        "worker_locked_at": None,
        "last_worker_run_at": None,
    }
    result = await db.notification_campaigns.insert_one(document)
    document["_id"] = result.inserted_id

    await append_notification_audit_log(
        db,
        entity_type="campaign",
        entity_id=str(result.inserted_id),
        action="created",
        admin=admin,
        metadata={
            "recipient_count": audience["estimated_recipients"],
            "recipient_type": payload["recipient_type"],
            "status": initial_status,
        },
        created_at=now,
    )

    if payload.get("send_now", True):
        from .notification_delivery import process_notification_campaign

        await process_notification_campaign(
            db,
            campaign_id=str(result.inserted_id),
            worker_id="api-immediate-send",
            claimed_campaign=document,
            now=now,
        )
        return await get_notification_campaign(db, str(result.inserted_id))

    await append_notification_audit_log(
        db,
        entity_type="campaign",
        entity_id=str(result.inserted_id),
        action="scheduled",
        admin=admin,
        metadata={"scheduled_for": _serialize_datetime(scheduled_for)},
        created_at=now,
    )
    return serialize_notification_campaign(document)


async def ensure_notification_preferences(db, *, user_id: str, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    existing = await db.notification_preferences.find_one({"user_id": user_id})
    if existing:
        return existing
    document = {
        "user_id": user_id,
        "preferences": deepcopy(DEFAULT_NOTIFICATION_PREFERENCES),
        "created_at": now,
        "updated_at": now,
    }
    await db.notification_preferences.insert_one(document)
    return document


async def get_notification_preferences(db, *, user_id: str, now: datetime | None = None) -> dict:
    document = await ensure_notification_preferences(db, user_id=user_id, now=now)
    return serialize_notification_preferences(document)


async def update_notification_preferences(db, *, user_id: str, payload: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    existing = await ensure_notification_preferences(db, user_id=user_id, now=now)
    values = {**DEFAULT_NOTIFICATION_PREFERENCES, **(existing.get("preferences") or {}), **payload}
    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": {"preferences": values, "updated_at": now}},
    )
    existing.update({"preferences": values, "updated_at": now})
    return serialize_notification_preferences(existing)


async def get_user_preferences_document(db, *, user_id: str, now: datetime | None = None) -> dict:
    document = await ensure_notification_preferences(db, user_id=user_id, now=now)
    return {**DEFAULT_NOTIFICATION_PREFERENCES, **(document.get("preferences") or {})}


def _is_notification_allowed_for_user(campaign: dict, preferences: dict, *, now: datetime) -> tuple[bool, str | None]:
    if not preferences.get("in_app_enabled", True):
        return False, "in_app_disabled"
    if _is_in_quiet_hours(preferences, now=now):
        return False, "quiet_hours"

    campaign_type = campaign.get("type", "notification")
    if campaign_type == "announcement" and not preferences.get("announcements_enabled", True):
        return False, "announcements_disabled"
    if campaign_type == "alert" and not preferences.get("alerts_enabled", True):
        return False, "alerts_disabled"
    if campaign_type == "notification" and not preferences.get("marketing_enabled", True):
        return False, "marketing_disabled"
    return True, None


async def list_notification_deliveries(db, *, campaign_id: str | None = None, user_id: str | None = None, unread_only: bool = False, limit: int = 100) -> list[dict]:
    query: dict = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if user_id:
        query["user_id"] = user_id
    if unread_only:
        query["status"] = "delivered"
        query["read_at"] = None
    deliveries = await db.notification_deliveries.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [serialize_notification_delivery(item) for item in deliveries]


async def list_notification_deliveries_page(
    db,
    *,
    campaign_id: str | None = None,
    user_id: str | None = None,
    unread_only: bool = False,
    cursor: str | None = None,
    page_size: int = 20,
) -> dict:
    query: dict = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if user_id:
        query["user_id"] = user_id
    if unread_only:
        query["status"] = "delivered"
        query["read_at"] = None

    total_items = await db.notification_deliveries.count_documents(query)
    effective_query = dict(query)
    if cursor:
        cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]

    rows = await db.notification_deliveries.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])

    return {
        "items": [serialize_notification_delivery(item) for item in rows],
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


async def mark_notification_delivery_as_read(db, *, delivery_id: str, user_id: str, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(delivery_id, detail="Invalid delivery_id")
    delivery = await db.notification_deliveries.find_one({"_id": object_id})
    if not delivery or delivery.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if delivery.get("read_at"):
        return serialize_notification_delivery(delivery)
    await db.notification_deliveries.update_one(
        {"_id": object_id},
        {"$set": {"read_at": now, "status": "read"}},
    )
    delivery.update({"read_at": now, "status": "read"})
    campaign_id = delivery.get("campaign_id")
    if campaign_id:
        await refresh_campaign_delivery_stats(db, campaign_id=campaign_id, now=now)
    return serialize_notification_delivery(delivery)


async def mark_all_user_notifications_as_read(db, *, user_id: str, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    unread_query = {
        "user_id": user_id,
        "read_at": None,
        "status": {"$in": ["delivered", "read"]},
    }
    affected_campaign_ids = set(
        await db.notification_deliveries.distinct("campaign_id", {**unread_query, "campaign_id": {"$ne": None}})
    )
    result = await db.notification_deliveries.update_many(
        unread_query,
        {"$set": {"read_at": now, "status": "read"}},
    )
    for campaign_id in affected_campaign_ids:
        await refresh_campaign_delivery_stats(db, campaign_id=campaign_id, now=now)
    return {"marked_read": result.modified_count}


async def get_user_notification_summary(db, *, user_id: str) -> dict:
    unread_count = await db.notification_deliveries.count_documents(
        {"user_id": user_id, "status": "delivered", "read_at": None}
    )
    inbox_count = await db.notification_deliveries.count_documents({"user_id": user_id})
    preferences = await get_notification_preferences(db, user_id=user_id)
    return {
        "unread_count": unread_count,
        "inbox_count": inbox_count,
        "preferences": preferences["preferences"],
    }


async def append_delivery_attempt(
    db,
    *,
    campaign_id: str,
    user_id: str,
    channel: str,
    adapter: str,
    status_value: str,
    delivery_id: str | None = None,
    failure_reason: str | None = None,
    metadata: dict | None = None,
    created_at: datetime | None = None,
):
    created_at = created_at or _utcnow()
    await db.notification_delivery_attempts.insert_one(
        {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "channel": channel,
            "adapter": adapter,
            "status": status_value,
            "delivery_id": delivery_id,
            "failure_reason": failure_reason,
            "metadata": metadata or {},
            "created_at": created_at,
        }
    )


async def record_worker_run(db, *, worker_id: str, status_value: str, claimed_campaigns: int, processed_campaigns: int, failed_campaigns: int, delivery_attempts: int, metadata: dict | None = None, last_error: str | None = None, started_at: datetime | None = None, finished_at: datetime | None = None):
    await db.notification_worker_runs.insert_one(
        {
            "worker_id": worker_id,
            "status": status_value,
            "claimed_campaigns": claimed_campaigns,
            "processed_campaigns": processed_campaigns,
            "failed_campaigns": failed_campaigns,
            "delivery_attempts": delivery_attempts,
            "metadata": metadata or {},
            "last_error": last_error,
            "started_at": started_at or _utcnow(),
            "finished_at": finished_at or _utcnow(),
        }
    )


async def list_worker_runs(db, *, limit: int = 25) -> list[dict]:
    runs = await db.notification_worker_runs.find({}).to_list(length=max(limit, 100))
    runs.sort(key=lambda item: item.get("started_at") or _utcnow(), reverse=True)
    return [serialize_worker_run(item) for item in runs[:limit]]


async def list_delivery_attempts(db, *, campaign_id: str | None = None, limit: int = 100) -> list[dict]:
    attempts = await db.notification_delivery_attempts.find({}).to_list(length=max(limit, 300))
    if campaign_id:
        attempts = [item for item in attempts if item.get("campaign_id") == campaign_id]
    attempts.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [
        {
            "_id": str(item.get("_id")),
            "campaign_id": item.get("campaign_id"),
            "user_id": item.get("user_id"),
            "channel": item.get("channel"),
            "adapter": item.get("adapter"),
            "status": item.get("status"),
            "delivery_id": item.get("delivery_id"),
            "failure_reason": item.get("failure_reason"),
            "metadata": item.get("metadata", {}),
            "created_at": _serialize_datetime(item.get("created_at")),
        }
        for item in attempts[:limit]
    ]


async def refresh_campaign_delivery_stats(db, *, campaign_id: str, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    deliveries = await db.notification_deliveries.find({}).to_list(length=5000)
    matched = [item for item in deliveries if item.get("campaign_id") == campaign_id]
    stats = {
        "accepted": len([item for item in matched if item.get("status") in {"delivered", "read", "suppressed", "failed"}]),
        "delivered": len([item for item in matched if item.get("status") in {"delivered", "read"}]),
        "opened": len([item for item in matched if item.get("read_at")]),
        "clicked": 0,
        "failed": len([item for item in matched if item.get("status") == "failed"]),
        "suppressed": len([item for item in matched if item.get("status") == "suppressed"]),
        "read": len([item for item in matched if item.get("status") == "read"]),
    }
    await db.notification_campaigns.update_one(
        {"_id": _to_object_id(campaign_id, detail="Invalid campaign_id")},
        {"$set": {"delivery_stats": stats, "updated_at": now}},
    )
    return stats


async def get_notification_summary(db) -> dict:
    campaigns = await db.notification_campaigns.find({}).to_list(length=500)
    templates = await db.notification_templates.find({}).to_list(length=500)
    alerts = await db.admin_alerts.find({}).to_list(length=500)
    worker_runs = await db.notification_worker_runs.find({}).to_list(length=200)
    latest_run = None
    if worker_runs:
        worker_runs.sort(key=lambda item: item.get("started_at") or _utcnow(), reverse=True)
        latest_run = serialize_worker_run(worker_runs[0])
    return {
        "totals": {
            "templates": len(templates),
            "campaigns": len(campaigns),
            "scheduled": sum(1 for item in campaigns if item.get("status") == "scheduled"),
            "processing": sum(1 for item in campaigns if item.get("status") == "processing"),
            "sent": sum(1 for item in campaigns if item.get("status") == "sent"),
            "failed": sum(1 for item in campaigns if item.get("status") == "failed"),
        },
        "admin_alerts": {
            "unread_count": sum(1 for item in alerts if not item.get("read")),
            "total": len(alerts),
        },
        "worker": {
            "latest_run": latest_run,
        },
    }

"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, status


NOTIFICATION_TYPE_LABELS = {
    "notification": "Notification",
    "announcement": "Announcement",
    "alert": "Alert",
}

NOTIFICATION_STATUS_LABELS = {
    "draft": "Draft",
    "scheduled": "Scheduled",
    "processing": "Processing",
    "sent": "Sent",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

ADMIN_ALERT_SEVERITY_LABELS = {
    "info": "Info",
    "warning": "Warning",
    "error": "Error",
}

DEFAULT_NOTIFICATION_PREFERENCES = {
    "in_app_enabled": True,
    "marketing_enabled": True,
    "announcements_enabled": True,
    "alerts_enabled": True,
    "quiet_hours_enabled": False,
    "quiet_hours_start": None,
    "quiet_hours_end": None,
    "timezone": "UTC",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def _to_object_id(value: str, *, detail: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


def _normalize_recipient_filter(payload: dict | None) -> dict:
    data = deepcopy(payload or {})
    return {
        "active_only": bool(data.get("active_only", False)),
        "last_active_days": data.get("last_active_days"),
    }


def _user_last_activity(user: dict):
    return user.get("last_login") or user.get("updated_at") or user.get("created_at")


def _safe_zoneinfo(tz_name: Optional[str]):
    try:
        return ZoneInfo(tz_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _parse_clock_minutes(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    hour_str, minute_str = value.split(":")
    return int(hour_str) * 60 + int(minute_str)


def _is_quiet_hours_active(preferences: dict, *, now: datetime) -> bool:
    if not preferences.get("quiet_hours_enabled"):
        return False
    start_value = _parse_clock_minutes(preferences.get("quiet_hours_start"))
    end_value = _parse_clock_minutes(preferences.get("quiet_hours_end"))
    if start_value is None or end_value is None:
        return False

    local_now = now.astimezone(_safe_zoneinfo(preferences.get("timezone")))
    current_minutes = local_now.hour * 60 + local_now.minute
    if start_value == end_value:
        return True
    if start_value < end_value:
        return start_value <= current_minutes < end_value
    return current_minutes >= start_value or current_minutes < end_value


def _matches_recipient(user: dict, recipient_type: str, recipient_filter: dict, *, now: datetime) -> bool:
    user_type = user.get("user_type")
    if recipient_type == "tourists" and user_type != "tourist":
        return False
    if recipient_type == "operators" and user_type != "operator":
        return False
    if recipient_type == "all" and user_type not in {"tourist", "operator"}:
        return False

    if recipient_filter.get("active_only") and user.get("is_active") is False:
        return False

    window_days = recipient_filter.get("last_active_days")
    if window_days:
        last_activity = _user_last_activity(user)
        if not isinstance(last_activity, datetime):
            return False
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        if last_activity < now - timedelta(days=int(window_days)):
            return False

    return True


async def list_matching_notification_users(db, *, recipient_type: str, recipient_filter: dict | None = None, now: datetime | None = None) -> list[dict]:
    now = now or _utcnow()
    normalized_filter = _normalize_recipient_filter(recipient_filter)
    users = await db.users.find({}).to_list(length=5000)
    return [
        user for user in users
        if _matches_recipient(user, recipient_type, normalized_filter, now=now)
    ]


async def preview_notification_audience(db, *, recipient_type: str, recipient_filter: dict | None = None, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    normalized_filter = _normalize_recipient_filter(recipient_filter)
    matched = await list_matching_notification_users(
        db,
        recipient_type=recipient_type,
        recipient_filter=normalized_filter,
        now=now,
    )

    breakdown = {
        "tourists": sum(1 for user in matched if user.get("user_type") == "tourist"),
        "operators": sum(1 for user in matched if user.get("user_type") == "operator"),
    }

    return {
        "recipient_type": recipient_type,
        "recipient_filter": normalized_filter,
        "estimated_recipients": len(matched),
        "breakdown": breakdown,
        "as_of": _serialize_datetime(now),
    }


def serialize_notification_template(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "name": document.get("name"),
        "category": document.get("category"),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "channels": document.get("channels", ["in_app"]),
        "is_active": bool(document.get("is_active", True)),
        "created_at": _serialize_datetime(document.get("created_at")),
        "updated_at": _serialize_datetime(document.get("updated_at")),
        "created_by": document.get("created_by"),
        "updated_by": document.get("updated_by"),
    }


def serialize_notification_campaign(document: dict) -> dict:
    campaign_type = document.get("type", "notification")
    status_value = document.get("status", "draft")
    return {
        "_id": str(document.get("_id")),
        "type": campaign_type,
        "type_label": NOTIFICATION_TYPE_LABELS.get(campaign_type, campaign_type.title()),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "channel": document.get("channel", "in_app"),
        "recipient_type": document.get("recipient_type"),
        "recipient_filter": document.get("recipient_filter", {}),
        "recipient_count": int(document.get("recipient_count", 0) or 0),
        "status": status_value,
        "status_label": NOTIFICATION_STATUS_LABELS.get(status_value, status_value.title()),
        "scheduled_for": _serialize_datetime(document.get("scheduled_for")),
        "sent_at": _serialize_datetime(document.get("sent_at")),
        "created_at": _serialize_datetime(document.get("created_at")),
        "updated_at": _serialize_datetime(document.get("updated_at")),
        "template_id": document.get("template_id"),
        "delivery_stats": document.get("delivery_stats", {}),
        "metadata": document.get("metadata", {}),
        "worker": {
            "locked_at": _serialize_datetime(document.get("worker_locked_at")),
            "lock_id": document.get("worker_lock_id"),
            "processed_at": _serialize_datetime(document.get("processed_at")),
            "last_error": document.get("last_error"),
        },
        "created_by": document.get("created_by"),
        "updated_by": document.get("updated_by"),
    }


def serialize_admin_alert(document: dict) -> dict:
    severity = document.get("severity", "info")
    return {
        "_id": str(document.get("_id")),
        "title": document.get("title"),
        "message": document.get("message"),
        "severity": severity,
        "severity_label": ADMIN_ALERT_SEVERITY_LABELS.get(severity, severity.title()),
        "category": document.get("category", "notification"),
        "service": document.get("service", "notification"),
        "read": bool(document.get("read", False)),
        "created_at": _serialize_datetime(document.get("created_at")),
        "read_at": _serialize_datetime(document.get("read_at")),
        "source_reference_type": document.get("source_reference_type"),
        "source_reference_id": document.get("source_reference_id"),
        "metadata": document.get("metadata", {}),
    }


def serialize_worker_run(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "status": document.get("status", "completed"),
        "started_at": _serialize_datetime(document.get("started_at")),
        "finished_at": _serialize_datetime(document.get("finished_at")),
        "claimed_campaigns": document.get("claimed_campaigns", 0),
        "processed_campaigns": document.get("processed_campaigns", 0),
        "failed_campaigns": document.get("failed_campaigns", 0),
        "summary": document.get("summary", {}),
        "last_error": document.get("last_error"),
    }


def serialize_delivery_attempt(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "campaign_id": document.get("campaign_id"),
        "user_id": document.get("user_id"),
        "channel": document.get("channel", "in_app"),
        "adapter": document.get("adapter", "in_app"),
        "status": document.get("status"),
        "reason": document.get("reason"),
        "delivery_id": document.get("delivery_id"),
        "campaign_subject": document.get("campaign_subject"),
        "user_email": document.get("user_email"),
        "user_type": document.get("user_type"),
        "created_at": _serialize_datetime(document.get("created_at")),
        "metadata": document.get("metadata", {}),
    }


def serialize_notification_delivery(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "campaign_id": document.get("campaign_id"),
        "user_id": document.get("user_id"),
        "type": document.get("type", "notification"),
        "type_label": NOTIFICATION_TYPE_LABELS.get(document.get("type", "notification"), "Notification"),
        "subject": document.get("subject"),
        "message": document.get("message"),
        "channel": document.get("channel", "in_app"),
        "status": document.get("status", "delivered"),
        "created_at": _serialize_datetime(document.get("created_at")),
        "delivered_at": _serialize_datetime(document.get("delivered_at")),
        "read": bool(document.get("read", False)),
        "read_at": _serialize_datetime(document.get("read_at")),
        "campaign": {
            "id": document.get("campaign_id"),
            "recipient_type": document.get("campaign_recipient_type"),
        },
        "metadata": document.get("metadata", {}),
    }


def serialize_notification_preferences(document: dict) -> dict:
    value = {**DEFAULT_NOTIFICATION_PREFERENCES, **deepcopy(document.get("value") or {})}
    return {
        "user_id": document.get("user_id"),
        "preferences": value,
        "updated_at": _serialize_datetime(document.get("updated_at")),
    }


async def append_notification_audit_log(db, *, entity_type: str, entity_id: str, action: str, admin: dict, metadata: dict | None = None, created_at: datetime | None = None):
    created_at = created_at or _utcnow()
    await db.notification_audit_log.insert_one(
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_id": admin.get("_id"),
            "actor_name": admin.get("full_name") or admin.get("email") or "Admin",
            "created_at": created_at,
            "metadata": metadata or {},
        }
    )


async def append_admin_alert(
    db,
    *,
    title: str,
    message: str,
    severity: str = "info",
    category: str = "notification",
    service: str = "notification",
    source_reference_type: str | None = None,
    source_reference_id: str | None = None,
    metadata: dict | None = None,
    created_at: datetime | None = None,
):
    created_at = created_at or _utcnow()
    await db.admin_alerts.insert_one(
        {
            "title": title,
            "message": message,
            "severity": severity,
            "category": category,
            "service": service,
            "read": False,
            "created_at": created_at,
            "read_at": None,
            "source_reference_type": source_reference_type,
            "source_reference_id": source_reference_id,
            "metadata": metadata or {},
        }
    )


async def log_notification_worker_run(db, payload: dict):
    await db.notification_worker_runs.insert_one(payload)


async def append_delivery_attempt(db, payload: dict):
    await db.notification_delivery_attempts.insert_one(payload)


async def get_notification_preferences_document(db, user_id: str, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    existing = await db.notification_preferences.find_one({"user_id": user_id})
    if existing:
        existing["value"] = {**DEFAULT_NOTIFICATION_PREFERENCES, **deepcopy(existing.get("value") or {})}
        return existing

    document = {
        "user_id": user_id,
        "value": deepcopy(DEFAULT_NOTIFICATION_PREFERENCES),
        "created_at": now,
        "updated_at": now,
    }
    await db.notification_preferences.insert_one(document)
    return document


async def get_user_notification_preferences(db, user_id: str, *, now: datetime | None = None) -> dict:
    return serialize_notification_preferences(
        await get_notification_preferences_document(db, user_id, now=now)
    )


async def update_user_notification_preferences(db, user_id: str, payload: dict, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    existing = await get_notification_preferences_document(db, user_id, now=now)
    merged = {**deepcopy(existing.get("value") or {}), **deepcopy(payload)}
    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": {"value": merged, "updated_at": now}},
    )
    existing["value"] = merged
    existing["updated_at"] = now
    return serialize_notification_preferences(existing)


def should_deliver_campaign_to_user(campaign: dict, preferences: dict, *, now: datetime) -> tuple[bool, str | None]:
    prefs = {**DEFAULT_NOTIFICATION_PREFERENCES, **deepcopy(preferences or {})}
    if not prefs.get("in_app_enabled", True):
        return False, "in_app_disabled"

    campaign_type = campaign.get("type", "notification")
    if campaign_type == "announcement" and not prefs.get("announcements_enabled", True):
        return False, "announcements_disabled"
    if campaign_type == "alert" and not prefs.get("alerts_enabled", True):
        return False, "alerts_disabled"
    if campaign_type == "notification" and not prefs.get("marketing_enabled", True):
        return False, "marketing_disabled"
    if _is_quiet_hours_active(prefs, now=now):
        return False, "quiet_hours_active"
    return True, None


async def list_notification_templates(db) -> list[dict]:
    templates = await db.notification_templates.find({}).to_list(length=200)
    templates.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_notification_template(item) for item in templates]


async def create_notification_template(db, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    document = {
        "name": payload["name"],
        "category": payload["category"],
        "subject": payload["subject"],
        "message": payload["message"],
        "channels": payload.get("channels", ["in_app"]),
        "is_active": bool(payload.get("is_active", True)),
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
    }
    result = await db.notification_templates.insert_one(document)
    document["_id"] = result.inserted_id
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=str(result.inserted_id),
        action="created",
        admin=admin,
        metadata={"name": document["name"]},
        created_at=now,
    )
    return serialize_notification_template(document)


async def update_notification_template(db, template_id: str, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(template_id, detail="Invalid template_id")
    existing = await db.notification_templates.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")

    updates = {
        **payload,
        "updated_at": now,
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
    }
    await db.notification_templates.update_one({"_id": object_id}, {"$set": updates})
    existing.update(updates)
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=template_id,
        action="updated",
        admin=admin,
        metadata={"updated_fields": sorted(payload.keys())},
        created_at=now,
    )
    return serialize_notification_template(existing)


async def delete_notification_template(db, template_id: str, *, admin: dict, now: datetime | None = None) -> None:
    now = now or _utcnow()
    object_id = _to_object_id(template_id, detail="Invalid template_id")
    existing = await db.notification_templates.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")

    linked_campaign = await db.notification_campaigns.find_one({"template_id": template_id})
    if linked_campaign:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is already referenced by an existing campaign",
        )

    await db.notification_templates.delete_one({"_id": object_id})
    await append_notification_audit_log(
        db,
        entity_type="template",
        entity_id=template_id,
        action="deleted",
        admin=admin,
        metadata={"name": existing.get("name")},
        created_at=now,
    )


async def list_notification_campaigns(db, *, campaign_type: str | None = None, status_value: str | None = None) -> list[dict]:
    campaigns = await db.notification_campaigns.find({}).to_list(length=300)
    if campaign_type:
        campaigns = [item for item in campaigns if item.get("type") == campaign_type]
    if status_value:
        campaigns = [item for item in campaigns if item.get("status") == status_value]
    campaigns.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_notification_campaign(item) for item in campaigns]


async def get_notification_campaign_document(db, campaign_id: str) -> dict:
    object_id = _to_object_id(campaign_id, detail="Invalid campaign_id")
    campaign = await db.notification_campaigns.find_one({"_id": object_id})
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification campaign not found")
    return campaign


async def get_notification_campaign(db, campaign_id: str) -> dict:
    return serialize_notification_campaign(await get_notification_campaign_document(db, campaign_id))


def _initial_delivery_stats(accepted: int = 0) -> dict:
    return {
        "accepted": accepted,
        "delivered": 0,
        "suppressed": 0,
        "opened": 0,
        "clicked": 0,
        "failed": 0,
    }


async def create_notification_campaign(db, payload: dict, *, admin: dict, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    audience = await preview_notification_audience(
        db,
        recipient_type=payload["recipient_type"],
        recipient_filter=payload.get("recipient_filter"),
        now=now,
    )

    scheduled_for = payload.get("scheduled_for")
    if scheduled_for and scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    send_now = payload.get("send_now", True)
    if not send_now and (scheduled_for is None or scheduled_for <= now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scheduled_for must be in the future")

    status_value = "processing" if send_now else "scheduled"
    document = {
        "type": payload.get("type", "notification"),
        "subject": payload["subject"],
        "message": payload["message"],
        "channel": payload.get("channel", "in_app"),
        "recipient_type": payload["recipient_type"],
        "recipient_filter": audience["recipient_filter"],
        "recipient_count": audience["estimated_recipients"],
        "status": status_value,
        "scheduled_for": scheduled_for,
        "sent_at": None,
        "created_at": now,
        "updated_at": now,
        "template_id": payload.get("template_id"),
        "metadata": payload.get("metadata", {}),
        "created_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "updated_by": admin.get("email") or admin.get("full_name") or admin.get("_id"),
        "delivery_stats": _initial_delivery_stats(audience["estimated_recipients"] if send_now else 0),
        "worker_locked_at": now if send_now else None,
        "worker_lock_id": f"inline:{now.timestamp()}" if send_now else None,
        "processed_at": None,
        "last_error": None,
    }
    result = await db.notification_campaigns.insert_one(document)
    document["_id"] = result.inserted_id
    action = "processing" if send_now else "scheduled"
    await append_notification_audit_log(
        db,
        entity_type="campaign",
        entity_id=str(result.inserted_id),
        action=action,
        admin=admin,
        metadata={
            "recipient_count": audience["estimated_recipients"],
            "recipient_type": payload["recipient_type"],
        },
        created_at=now,
    )

    if send_now:
        from .notification_delivery import process_notification_campaign

        processed = await process_notification_campaign(
            db,
            campaign_id=str(result.inserted_id),
            triggered_by="admin_request",
            lock_id=document["worker_lock_id"],
            now=now,
        )
        return serialize_notification_campaign(processed)

    return serialize_notification_campaign(document)


async def list_admin_alerts(db, *, unread_only: bool = False) -> list[dict]:
    alerts = await db.admin_alerts.find({}).to_list(length=200)
    if unread_only:
        alerts = [item for item in alerts if not item.get("read")]
    alerts.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_admin_alert(item) for item in alerts]


async def mark_admin_alert_read(db, alert_id: str, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(alert_id, detail="Invalid alert_id")
    alert = await db.admin_alerts.find_one({"_id": object_id})
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin alert not found")
    await db.admin_alerts.update_one({"_id": object_id}, {"$set": {"read": True, "read_at": now}})
    alert["read"] = True
    alert["read_at"] = now
    return serialize_admin_alert(alert)


async def mark_all_admin_alerts_read(db, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    alerts = await db.admin_alerts.find({}).to_list(length=500)
    changed = 0
    for alert in alerts:
        if alert.get("read"):
            continue
        changed += 1
        await db.admin_alerts.update_one({"_id": alert["_id"]}, {"$set": {"read": True, "read_at": now}})
    return {"updated": changed}


async def list_notification_worker_runs(db) -> list[dict]:
    runs = await db.notification_worker_runs.find({}).to_list(length=100)
    runs.sort(key=lambda item: item.get("started_at") or _utcnow(), reverse=True)
    return [serialize_worker_run(item) for item in runs]


async def list_notification_delivery_attempts(db, *, campaign_id: str | None = None) -> list[dict]:
    attempts = await db.notification_delivery_attempts.find({}).to_list(length=300)
    if campaign_id:
        attempts = [item for item in attempts if item.get("campaign_id") == campaign_id]
    attempts.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_delivery_attempt(item) for item in attempts]


async def list_user_notification_deliveries(db, user_id: str, *, unread_only: bool = False) -> list[dict]:
    deliveries = await db.notification_deliveries.find({}).to_list(length=300)
    deliveries = [item for item in deliveries if item.get("user_id") == user_id and item.get("status") == "delivered"]
    if unread_only:
        deliveries = [item for item in deliveries if not item.get("read")]
    deliveries.sort(key=lambda item: item.get("created_at") or _utcnow(), reverse=True)
    return [serialize_notification_delivery(item) for item in deliveries]


async def mark_notification_delivery_read(db, user_id: str, delivery_id: str, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    object_id = _to_object_id(delivery_id, detail="Invalid delivery_id")
    delivery = await db.notification_deliveries.find_one({"_id": object_id})
    if not delivery or delivery.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not delivery.get("read"):
        await db.notification_deliveries.update_one(
            {"_id": object_id},
            {"$set": {"read": True, "read_at": now}},
        )
        delivery["read"] = True
        delivery["read_at"] = now
    return serialize_notification_delivery(delivery)


async def mark_all_user_notification_deliveries_read(db, user_id: str, *, now: datetime | None = None) -> dict:
    now = now or _utcnow()
    deliveries = await db.notification_deliveries.find({}).to_list(length=500)
    changed = 0
    for delivery in deliveries:
        if delivery.get("user_id") != user_id or delivery.get("read"):
            continue
        changed += 1
        await db.notification_deliveries.update_one(
            {"_id": delivery["_id"]},
            {"$set": {"read": True, "read_at": now}},
        )
    return {"updated": changed}


async def get_notification_summary(db) -> dict:
    campaigns = await db.notification_campaigns.find({}).to_list(length=500)
    templates = await db.notification_templates.find({}).to_list(length=500)
    alerts = await db.admin_alerts.find({}).to_list(length=500)
    worker_runs = await db.notification_worker_runs.find({}).to_list(length=100)
    deliveries = await db.notification_deliveries.find({}).to_list(length=1000)
    attempts = await db.notification_delivery_attempts.find({}).to_list(length=1000)
    return {
        "totals": {
            "templates": len(templates),
            "campaigns": len(campaigns),
            "scheduled": sum(1 for item in campaigns if item.get("status") == "scheduled"),
            "processing": sum(1 for item in campaigns if item.get("status") == "processing"),
            "sent": sum(1 for item in campaigns if item.get("status") == "sent"),
            "failed": sum(1 for item in campaigns if item.get("status") == "failed"),
            "admin_alerts_unread": sum(1 for item in alerts if not item.get("read")),
            "inbox_deliveries": sum(1 for item in deliveries if item.get("status") == "delivered"),
            "suppressed_deliveries": sum(1 for item in attempts if item.get("status") == "suppressed"),
        },
        "worker": {
            "runs": len(worker_runs),
            "last_run_at": _serialize_datetime(worker_runs[-1].get("finished_at")) if worker_runs else None,
        },
    }


async def get_user_notification_summary(db, user_id: str) -> dict:
    deliveries = await db.notification_deliveries.find({}).to_list(length=500)
    unread_count = sum(
        1 for item in deliveries
        if item.get("user_id") == user_id and item.get("status") == "delivered" and not item.get("read")
    )
    preferences = await get_user_notification_preferences(db, user_id)
    return {
        "unread_count": unread_count,
        "preferences": preferences["preferences"],
    }
"""
