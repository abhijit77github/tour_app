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


async def record_authorization_decision(
    db,
    *,
    principal_type: str,
    principal_id: str | None,
    principal_name: str | None,
    permission: str | None,
    path: str,
    method: str,
    decision: str,
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    severity = "warning" if decision == "denied" else "info"
    await append_audit_event_safe(
        db,
        category="security",
        title=f"Authorization {decision}",
        severity=severity,
        event_type="authorization_decision",
        user_name=principal_name or f"{principal_type}:{principal_id or 'unknown'}",
        location="API",
        description=detail or f"Authorization {decision} for {method} {path}",
        metadata={
            "principal_type": principal_type,
            "principal_id": principal_id,
            "permission": permission,
            "path": path,
            "method": method,
            "decision": decision,
            **(metadata or {}),
        },
    )


def serialize_audit_event(document: dict) -> dict:
    item = dict(document)
    item["_id"] = str(item["_id"])
    for field in ("timestamp", "created_at", "updated_at"):
        if item.get(field):
            item[field] = item[field].isoformat()
    return item


def _nested_value(document: dict, path: str):
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _safe_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return None


async def build_authorization_decision_report(
    db,
    *,
    hours: int = 24,
    limit: int = 200,
    principal_type: str | None = None,
    decision: str | None = None,
    permission: str | None = None,
    path_contains: str | None = None,
) -> dict:
    safe_hours = max(int(hours or 24), 1)
    safe_limit = min(max(int(limit or 200), 1), 1000)
    since = utcnow() - timedelta(hours=safe_hours)

    base_filters: dict[str, Any] = {
        "category": "security",
        "event_type": "authorization_decision",
        "timestamp": {"$gte": since},
    }

    normalized_principal_type = principal_type.strip().casefold() if principal_type else ""
    normalized_decision = decision.strip().casefold() if decision else ""
    normalized_permission = permission.strip() if permission else ""
    normalized_path_contains = path_contains.strip().casefold() if path_contains else ""

    if normalized_principal_type:
        base_filters["metadata.principal_type"] = normalized_principal_type
    if normalized_decision:
        base_filters["metadata.decision"] = normalized_decision
    if normalized_permission:
        base_filters["metadata.permission"] = normalized_permission

    all_docs = await db[AUDIT_EVENTS_COLLECTION].find(base_filters).sort("timestamp", -1).to_list(length=5000)
    if normalized_path_contains:
        all_docs = [
            doc
            for doc in all_docs
            if normalized_path_contains in str(_nested_value(doc, "metadata.path") or "").casefold()
        ]

    allowed_count = sum(1 for doc in all_docs if str(_nested_value(doc, "metadata.decision") or "").casefold() == "allowed")
    denied_count = sum(1 for doc in all_docs if str(_nested_value(doc, "metadata.decision") or "").casefold() == "denied")
    total_count = len(all_docs)

    permission_denials: dict[str, int] = {}
    route_denials: dict[str, int] = {}
    principal_activity: dict[str, dict[str, int]] = {}

    for doc in all_docs:
        decision_value = str(_nested_value(doc, "metadata.decision") or "").casefold()
        permission_value = str(_nested_value(doc, "metadata.permission") or "none")
        route_value = f"{_nested_value(doc, 'metadata.method') or ''} {_nested_value(doc, 'metadata.path') or ''}".strip()
        principal_value = str(_nested_value(doc, "metadata.principal_type") or "unknown")

        if principal_value not in principal_activity:
            principal_activity[principal_value] = {"allowed": 0, "denied": 0, "total": 0}
        principal_activity[principal_value]["total"] += 1
        if decision_value == "denied":
            principal_activity[principal_value]["denied"] += 1
            permission_denials[permission_value] = permission_denials.get(permission_value, 0) + 1
            route_denials[route_value] = route_denials.get(route_value, 0) + 1
        else:
            principal_activity[principal_value]["allowed"] += 1

    def _top_rows(counter: dict[str, int], label: str) -> list[dict]:
        return [
            {label: key, "count": value}
            for key, value in sorted(counter.items(), key=lambda item: item[1], reverse=True)[:10]
        ]

    recent_events = []
    for doc in all_docs[:safe_limit]:
        recent_events.append(
            {
                "timestamp": _safe_iso(doc.get("timestamp")),
                "principal_type": _nested_value(doc, "metadata.principal_type"),
                "principal_id": _nested_value(doc, "metadata.principal_id"),
                "decision": _nested_value(doc, "metadata.decision"),
                "permission": _nested_value(doc, "metadata.permission"),
                "method": _nested_value(doc, "metadata.method"),
                "path": _nested_value(doc, "metadata.path"),
                "detail": doc.get("description"),
            }
        )

    denial_rate = round((denied_count / total_count) * 100, 2) if total_count else 0.0
    return {
        "window": {
            "hours": safe_hours,
            "since": since.isoformat(),
        },
        "filters": {
            "principal_type": normalized_principal_type or None,
            "decision": normalized_decision or None,
            "permission": normalized_permission or None,
            "path_contains": normalized_path_contains or None,
        },
        "summary": {
            "total": total_count,
            "allowed": allowed_count,
            "denied": denied_count,
            "denialRate": denial_rate,
        },
        "topDeniedPermissions": _top_rows(permission_denials, "permission"),
        "topDeniedRoutes": _top_rows(route_denials, "route"),
        "principalBreakdown": [
            {
                "principal_type": key,
                "allowed": values["allowed"],
                "denied": values["denied"],
                "total": values["total"],
            }
            for key, values in sorted(principal_activity.items(), key=lambda item: item[1]["total"], reverse=True)
        ],
        "events": recent_events,
    }