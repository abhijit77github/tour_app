from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import settings

AUDIT_EVENTS_COLLECTION = "audit_events"

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def append_audit_event(
    db,
    *,
    category: str,
    title: str,
    severity: str = "info",
    timestamp: datetime | None = None,
    service: str | None = None,
    error_code: str | None = None,
    message: str | None = None,
    details: str | None = None,
    read: bool | None = None,
    event_type: str | None = None,
    user_name: str | None = None,
    ip_address: str | None = None,
    location: str | None = None,
    description: str | None = None,
    remediation: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    now = timestamp or utcnow()
    document = {
        "category": category,
        "title": title,
        "severity": severity,
        "timestamp": now,
        "service": service,
        "error_code": error_code,
        "message": message,
        "details": details,
        "read": bool(read) if read is not None else False,
        "event_type": event_type,
        "user_name": user_name,
        "ip_address": ip_address or "N/A",
        "location": location or "Unknown",
        "description": description,
        "remediation": remediation,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    result = await db[AUDIT_EVENTS_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def append_audit_event_safe(db, **kwargs) -> dict | None:
    try:
        return await append_audit_event(db, **kwargs)
    except Exception as exc:
        logger.warning("Failed to append audit event: %s", exc)
        return None


def get_login_alert_threshold() -> int:
    return max(int(settings.audit_login_alert_threshold or 3), 1)


def get_login_alert_window() -> timedelta:
    return timedelta(minutes=max(int(settings.audit_login_alert_window_minutes or 15), 1))


async def count_recent_login_failures(db, *, principal_type: str, email: str, since: datetime) -> int:
    return await db[AUDIT_EVENTS_COLLECTION].count_documents(
        {
            "category": "security",
            "event_type": "failed_login",
            "metadata.principal_type": principal_type,
            "metadata.email": email.casefold(),
            "timestamp": {"$gte": since},
        }
    )


async def record_login_security_event(
    db,
    *,
    principal_type: str,
    email: str,
    outcome: str,
    ip_address: str | None = None,
    location: str | None = None,
    user_name: str | None = None,
    user_id: str | None = None,
    description: str | None = None,
    remediation: str | None = None,
    threshold_enabled: bool = True,
) -> None:
    normalized_email = email.strip().casefold()
    normalized_principal = principal_type.strip().casefold()
    safe_user_name = user_name or normalized_email or principal_type.title()

    if outcome == "success":
        await append_audit_event_safe(
            db,
            category="security",
            title=f"{principal_type.title()} login succeeded",
            severity="info",
            event_type="login_success",
            user_name=safe_user_name,
            ip_address=ip_address,
            location=location,
            description=description or f"Successful login for {normalized_email}",
            remediation=remediation,
            metadata={
                "principal_type": normalized_principal,
                "email": normalized_email,
                "outcome": outcome,
                "user_id": user_id,
            },
        )
        return

    await append_audit_event_safe(
        db,
        category="security",
        title=f"{principal_type.title()} login failed",
        severity="warning",
        event_type="failed_login",
        user_name=safe_user_name,
        ip_address=ip_address,
        location=location,
        description=description or f"Failed login for {normalized_email}",
        remediation=remediation or "Review the account activity and verify the login source.",
        metadata={
            "principal_type": normalized_principal,
            "email": normalized_email,
            "outcome": outcome,
            "user_id": user_id,
        },
    )

    if not threshold_enabled or not normalized_email:
        return

    window_start = utcnow() - get_login_alert_window()
    failure_count = await count_recent_login_failures(
        db,
        principal_type=normalized_principal,
        email=normalized_email,
        since=window_start,
    )
    threshold = get_login_alert_threshold()
    if failure_count != threshold:
        return

    await append_audit_event_safe(
        db,
        category="security",
        title=f"{principal_type.title()} login threshold reached",
        severity="critical",
        event_type="brute_force",
        user_name=safe_user_name,
        ip_address=ip_address,
        location=location,
        description=(
            f"{failure_count} failed login attempts for {normalized_email} within "
            f"{int(get_login_alert_window().total_seconds() // 60)} minutes"
        ),
        remediation="Investigate potential credential stuffing or brute-force activity.",
        metadata={
            "principal_type": normalized_principal,
            "email": normalized_email,
            "threshold": threshold,
            "failure_count": failure_count,
            "user_id": user_id,
        },
    )


def serialize_audit_event(document: dict) -> dict:
    item = dict(document)
    item["_id"] = str(item["_id"])
    for field in ("timestamp", "created_at", "updated_at"):
        if item.get(field):
            item[field] = item[field].isoformat()
    return item