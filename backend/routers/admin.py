import base64
import csv
import io
import json
import math

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import Response
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from uuid import uuid4
from bson import ObjectId
from jose import jwt, JWTError
from functools import wraps
import os
import logging

from ..database import get_database
from ..models.admin import AdminCreate, AdminLogin, AdminToken, Admin
from ..models.promotion import LocationPromotionCreate, LocationPromotionUpdate
from ..routers.auth import get_current_user
from ..utils.auth import get_password_hash, verify_password as _verify_password
from ..utils.audit_events import (
    build_authorization_decision_report,
    record_authorization_decision,
    record_login_security_event,
    serialize_audit_event,
)
from ..utils.authorization import (
    ensure_admin_access_context,
    has_permission,
    is_recent_auth_payload,
    permission_requires_step_up,
    required_permission_for_request,
)
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Valid admin roles
VALID_ADMIN_ROLES = {"super_admin", "admin", "moderator"}

DASHBOARD_WIDGET_LABELS = {
    "revenue": "Revenue Chart",
    "bookings": "Bookings Graph",
    "operators": "Top Operators",
    "satisfaction": "Satisfaction Scores",
    "metrics": "Key Metrics",
}

DASHBOARD_WIDGET_NAME_TO_KEY = {
    value.casefold(): key for key, value in DASHBOARD_WIDGET_LABELS.items()
}


def _slugify_filename(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return cleaned or "report"


def _dashboard_query(document_id: str) -> dict:
    try:
        return {"_id": ObjectId(document_id)}
    except Exception:
        return {"_id": document_id}


def _normalize_dashboard_widgets(raw_widgets) -> list[dict]:
    widgets = []
    for item in raw_widgets or []:
        if isinstance(item, str):
            key = item.strip().casefold()
            name = DASHBOARD_WIDGET_LABELS.get(key, item.strip() or "Custom Widget")
        elif isinstance(item, dict):
            raw_key = str(item.get("key") or "").strip().casefold()
            raw_name = str(item.get("name") or "").strip()
            key = raw_key or DASHBOARD_WIDGET_NAME_TO_KEY.get(raw_name.casefold(), raw_name.casefold())
            name = raw_name or DASHBOARD_WIDGET_LABELS.get(key, "Custom Widget")
        else:
            continue

        if not key:
            continue
        widgets.append({"key": key, "name": DASHBOARD_WIDGET_LABELS.get(key, name)})

    deduped = []
    seen_keys = set()
    for widget in widgets:
        key = widget["key"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(widget)
    return deduped


def _serialize_dashboard(document: dict) -> dict:
    item = dict(document)
    item["_id"] = str(item["_id"])
    item["widgets"] = _normalize_dashboard_widgets(item.get("widgets") or [])
    item["shared_with"] = [str(entry).strip() for entry in item.get("shared_with") or [] if str(entry).strip()]
    item["description"] = item.get("description") or ""
    return item


def _normalize_location_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.casefold() if cleaned else None


def _coerce_utc_datetime(value):
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalize_pagination(page: int, per_page: int, *, maximum_per_page: int = 50) -> tuple[int, int]:
    safe_page = max(int(page or 1), 1)
    safe_per_page = min(max(int(per_page or 10), 1), maximum_per_page)
    return safe_page, safe_per_page


def _paginate_items(items: list[dict], page: int, per_page: int) -> tuple[list[dict], dict]:
    safe_page, safe_per_page = _normalize_pagination(page, per_page)
    total = len(items)
    total_pages = max(1, math.ceil(total / safe_per_page)) if safe_per_page else 1
    current_page = min(safe_page, total_pages)
    start_index = (current_page - 1) * safe_per_page
    end_index = start_index + safe_per_page
    return (
        items[start_index:end_index],
        {
            "page": current_page,
            "perPage": safe_per_page,
            "total": total,
            "totalPages": total_pages,
            "hasPrev": current_page > 1,
            "hasNext": current_page < total_pages,
        },
    )


def _parse_filter_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end_of_day:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    return parsed


def _request_ip(request: Request | None) -> str:
    if request and request.client and request.client.host:
        return request.client.host
    return "N/A"


def _build_audit_search_query(fields: list[str], search_value: str) -> dict:
    normalized_search = search_value.strip()
    if not normalized_search:
        return {}
    return {"$or": [{field: {"$regex": normalized_search, "$options": "i"}} for field in fields]}


async def _paginate_audit_events(collection, *, filters: dict, page: int, per_page: int) -> tuple[list[dict], dict]:
    safe_page, safe_per_page = _normalize_pagination(page, per_page)
    total = await collection.count_documents(filters)
    total_pages = max(1, math.ceil(total / safe_per_page)) if safe_per_page else 1
    current_page = min(safe_page, total_pages)
    documents = await collection.find(filters).sort("timestamp", -1).skip((current_page - 1) * safe_per_page).limit(safe_per_page).to_list(length=safe_per_page)
    return (
        [serialize_audit_event(document) for document in documents],
        {
            "page": current_page,
            "perPage": safe_per_page,
            "total": total,
            "totalPages": total_pages,
            "hasPrev": current_page > 1,
            "hasNext": current_page < total_pages,
        },
    )


def _encode_datetime_object_cursor(*, created_at: datetime, document_id: ObjectId) -> str:
    normalized_created_at = _coerce_utc_datetime(created_at)
    payload = {
        "created_at": normalized_created_at.isoformat(),
        "document_id": str(document_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _decode_datetime_object_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        created_at = _coerce_utc_datetime(datetime.fromisoformat(payload["created_at"]))
        document_id = ObjectId(payload["document_id"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
    return created_at, document_id


def _build_normalized_location_scope(scope: dict) -> dict:
    return {
        "area_name": _normalize_location_value(scope.get("area_name")),
        "state": _normalize_location_value(scope.get("state")),
        "country": _normalize_location_value(scope.get("country")),
    }


def _area_matches_scope(area: dict, scope: dict) -> bool:
    if scope.get("area_name") and _normalize_location_value(area.get("area_name")) != _normalize_location_value(scope.get("area_name")):
        return False
    if scope.get("state") and _normalize_location_value(area.get("state")) != _normalize_location_value(scope.get("state")):
        return False
    if scope.get("country") and _normalize_location_value(area.get("country")) != _normalize_location_value(scope.get("country")):
        return False
    return True


def _operator_supports_scope(profile: dict, scope: dict) -> bool:
    return any(_area_matches_scope(area, scope) for area in profile.get("serving_areas", []))


def _valid_object_ids(values: set[str] | list[str]) -> list[ObjectId]:
    object_ids: list[ObjectId] = []
    for value in values:
        try:
            object_ids.append(ObjectId(value))
        except Exception:
            continue
    return object_ids


async def _load_users_by_id(db, user_ids: set[str] | list[str]) -> dict[str, dict]:
    object_ids = _valid_object_ids(user_ids)
    if not object_ids:
        return {}
    users = await db.users.find(
        {"_id": {"$in": object_ids}},
        {"full_name": 1, "email": 1, "user_type": 1, "created_at": 1, "updated_at": 1, "last_login": 1, "is_active": 1},
    ).to_list(length=len(object_ids))
    return {str(user["_id"]): user for user in users}


async def _load_operator_profiles_by_id(db, profile_ids: set[str] | list[str]) -> dict[str, dict]:
    object_ids = _valid_object_ids(profile_ids)
    if not object_ids:
        return {}
    profiles = await db.operator_profiles.find(
        {"_id": {"$in": object_ids}},
        {"business_name": 1},
    ).to_list(length=len(object_ids))
    return {str(profile["_id"]): profile for profile in profiles}


def _default_admin_report_items(*, now: datetime, admin: dict) -> list[dict]:
    return [
        {
            "_id": "report-revenue-current-month",
            "name": f"Revenue Analysis - {now.strftime('%b %Y')}",
            "type": "revenue",
            "status": "completed",
            "size": "1.9 MB",
            "generated_by": "System",
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(days=1),
        },
        {
            "_id": "report-operator-performance",
            "name": "Operator Performance Snapshot",
            "type": "operators",
            "status": "completed",
            "size": "1.2 MB",
            "generated_by": "System",
            "created_at": now - timedelta(days=3),
            "updated_at": now - timedelta(days=2),
        },
        {
            "_id": "report-booking-trends",
            "name": "Booking Trends Summary",
            "type": "bookings",
            "status": "completed",
            "size": "1.4 MB",
            "generated_by": admin.get("full_name", "Admin User"),
            "created_at": now - timedelta(days=4),
            "updated_at": now - timedelta(days=3),
        },
        {
            "_id": "report-customer-acquisition",
            "name": "Customer Acquisition Overview",
            "type": "customers",
            "status": "draft",
            "size": "0.6 MB",
            "generated_by": admin.get("full_name", "Admin User"),
            "created_at": now - timedelta(days=1),
            "updated_at": now - timedelta(hours=12),
        },
    ]


async def _find_admin_report(db, report_id: str, admin: dict) -> dict:
    report = None
    try:
        report = await db.admin_reports.find_one({"_id": ObjectId(report_id)})
    except Exception:
        report = None

    if report is None:
        report = await db.admin_reports.find_one({"_id": report_id})

    if report is not None:
        report["_id"] = str(report["_id"])
        return report

    now = datetime.now(timezone.utc)
    for item in _default_admin_report_items(now=now, admin=admin):
        if item["_id"] == report_id:
            return item

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


async def _build_admin_report_payload(db, report: dict) -> dict:
    now = datetime.now(timezone.utc)
    report_type = str(report.get("type") or "general").lower()

    total_quotes = await db.quote_requests.count_documents({})
    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    total_bookings = await db.bookings.count_documents({})
    completed_bookings = await db.bookings.count_documents({"booking_status.status": "completed"})
    total_tourists = await db.users.count_documents({"user_type": "tourist"})
    total_operators = await db.operator_profiles.count_documents({})

    sections = []
    summary = "Operational report generated from current admin metrics."

    if report_type == "revenue":
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue_rows = await db.bookings.aggregate(
            [
                {"$match": {"booking_status.status": "completed"}},
                {
                    "$project": {
                        "amount": {"$ifNull": ["$final_cost", "$estimated_cost"]},
                        "created_at": 1,
                    }
                },
                {"$match": {"amount": {"$gt": 0}}},
                {
                    "$group": {
                        "_id": None,
                        "total_revenue": {"$sum": "$amount"},
                        "monthly_revenue": {
                            "$sum": {
                                "$cond": [{"$gte": ["$created_at", month_start]}, "$amount", 0]
                            }
                        },
                        "transaction_count": {"$sum": 1},
                    }
                },
            ]
        ).to_list(length=1)
        revenue_stats = revenue_rows[0] if revenue_rows else {}
        total_revenue = float(revenue_stats.get("total_revenue", 0) or 0)
        monthly_revenue = float(revenue_stats.get("monthly_revenue", 0) or 0)
        transaction_count = int(revenue_stats.get("transaction_count", 0) or 0)
        summary = "Revenue snapshot based on completed bookings and current month activity."
        sections.append(
            {
                "title": "Key Metrics",
                "kind": "stats",
                "items": [
                    {"label": "Total revenue", "value": round(total_revenue, 2)},
                    {"label": "Monthly revenue", "value": round(monthly_revenue, 2)},
                    {"label": "Completed bookings", "value": completed_bookings},
                    {"label": "Average transaction", "value": round(total_revenue / transaction_count, 2) if transaction_count else 0},
                ],
            }
        )
    elif report_type == "operators":
        operator_rows = await db.bookings.aggregate(
            [
                {"$match": {"operator_id": {"$exists": True, "$ne": None}, "booking_status.status": {"$in": ["completed", "confirmed"]}}},
                {"$group": {"_id": "$operator_id", "bookings": {"$sum": 1}}},
                {"$sort": {"bookings": -1}},
                {"$limit": 5},
            ]
        ).to_list(length=5)
        profiles = await _load_operator_profiles_by_id(db, {str(item.get("_id")) for item in operator_rows})
        summary = "Operator activity snapshot based on assigned completed and confirmed bookings."
        sections.append(
            {
                "title": "Key Metrics",
                "kind": "stats",
                "items": [
                    {"label": "Operator profiles", "value": total_operators},
                    {"label": "Completed bookings", "value": completed_bookings},
                    {"label": "Closed quotes", "value": closed_quotes},
                ],
            }
        )
        sections.append(
            {
                "title": "Top operators",
                "kind": "table",
                "columns": ["Operator", "Bookings"],
                "rows": [
                    [
                        profiles.get(str(item.get("_id")), {}).get("business_name", "Unknown operator"),
                        int(item.get("bookings", 0) or 0),
                    ]
                    for item in operator_rows
                ],
            }
        )
    elif report_type == "bookings":
        pending_bookings = await db.bookings.count_documents({"booking_status.status": {"$in": ["pending", "confirmed"]}})
        cancelled_bookings = await db.bookings.count_documents({"booking_status.status": "cancelled"})
        summary = "Booking flow summary across total, completed, pending, and cancelled states."
        sections.append(
            {
                "title": "Key Metrics",
                "kind": "stats",
                "items": [
                    {"label": "Total bookings", "value": total_bookings},
                    {"label": "Completed", "value": completed_bookings},
                    {"label": "Pending or confirmed", "value": pending_bookings},
                    {"label": "Cancelled", "value": cancelled_bookings},
                ],
            }
        )
    elif report_type == "customers":
        recent_cutoff = now - timedelta(days=30)
        new_tourists = await db.users.count_documents({"user_type": "tourist", "created_at": {"$gte": recent_cutoff}})
        summary = "Customer acquisition summary based on tourist registrations and quote activity."
        sections.append(
            {
                "title": "Key Metrics",
                "kind": "stats",
                "items": [
                    {"label": "Total tourists", "value": total_tourists},
                    {"label": "New tourists (30d)", "value": new_tourists},
                    {"label": "Total quotes", "value": total_quotes},
                    {"label": "Closed quotes", "value": closed_quotes},
                ],
            }
        )
    else:
        sections.append(
            {
                "title": "Key Metrics",
                "kind": "stats",
                "items": [
                    {"label": "Total quotes", "value": total_quotes},
                    {"label": "Total bookings", "value": total_bookings},
                    {"label": "Total operators", "value": total_operators},
                    {"label": "Total tourists", "value": total_tourists},
                ],
            }
        )

    return {
        "report": report,
        "generated_at": now,
        "summary": summary,
        "sections": sections,
    }


def _report_payload_to_csv(payload: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    report = payload.get("report") or {}

    writer.writerow(["Report", report.get("name", "Unknown")])
    writer.writerow(["Type", report.get("type", "general")])
    writer.writerow(["Status", report.get("status", "unknown")])
    writer.writerow(["Generated At", payload.get("generated_at")])
    writer.writerow([])

    for section in payload.get("sections", []):
        writer.writerow([section.get("title", "Section")])
        if section.get("kind") == "stats":
            writer.writerow(["Label", "Value"])
            for item in section.get("items", []):
                writer.writerow([item.get("label", ""), item.get("value", "")])
        elif section.get("kind") == "table":
            writer.writerow(section.get("columns", []))
            for row in section.get("rows", []):
                writer.writerow(row)
        writer.writerow([])

    return output.getvalue()


def _report_payload_to_text_lines(payload: dict) -> list[str]:
    report = payload.get("report") or {}
    lines = [
        report.get("name", "Report"),
        f"Type: {report.get('type', 'general')}",
        f"Status: {report.get('status', 'unknown')}",
        f"Generated by: {report.get('generated_by', 'Unknown')}",
        f"Generated at: {payload.get('generated_at')}",
        "",
        payload.get("summary", ""),
        "",
    ]

    for section in payload.get("sections", []):
        lines.append(section.get("title", "Section"))
        if section.get("kind") == "stats":
            for item in section.get("items", []):
                lines.append(f"- {item.get('label', '')}: {item.get('value', '')}")
        elif section.get("kind") == "table":
            columns = section.get("columns", [])
            if columns:
                lines.append(" | ".join(str(column) for column in columns))
            for row in section.get("rows", []):
                lines.append(" | ".join(str(cell) for cell in row))
        lines.append("")

    return lines


def _render_text_pdf(lines: list[str]) -> bytes:
    safe_lines = [str(line) for line in lines if line is not None]

    def _escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_lines = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
    first_line = True
    for line in safe_lines:
        escaped = _escape_pdf_text(line)
        if first_line:
            content_lines.append(f"({escaped}) Tj")
            first_line = False
        else:
            content_lines.append(f"T* ({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)


async def _load_operator_response_stats(db, operator_profile_ids: set[str] | list[str]) -> dict[str, dict]:
    profile_ids = [profile_id for profile_id in operator_profile_ids if profile_id]
    if not profile_ids:
        return {}

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    stats_rows = await db.quote_requests.aggregate(
        [
            {"$match": {"responses.0": {"$exists": True}}},
            {"$unwind": "$responses"},
            {"$match": {"responses.operator_id": {"$in": profile_ids}}},
            {
                "$project": {
                    "operator_id": "$responses.operator_id",
                    "quote_created_at": "$created_at",
                    "response_created_at": {"$ifNull": ["$responses.created_at", "$created_at"]},
                }
            },
            {
                "$group": {
                    "_id": "$operator_id",
                    "total_responses": {"$sum": 1},
                    "recent_responses_30d": {
                        "$sum": {
                            "$cond": [{"$gte": ["$response_created_at", thirty_days_ago]}, 1, 0]
                        }
                    },
                    "average_response_time_ms": {
                        "$avg": {"$subtract": ["$response_created_at", "$quote_created_at"]}
                    },
                }
            },
        ]
    ).to_list(length=None)

    stats_by_profile: dict[str, dict] = {}
    for row in stats_rows:
        average_response_time_ms = row.get("average_response_time_ms") or 0
        stats_by_profile[row["_id"]] = {
            "total_responses": row.get("total_responses", 0),
            "recent_responses_30d": row.get("recent_responses_30d", 0),
            "avg_response_time_hours": round(average_response_time_ms / 3600000, 2),
        }
    return stats_by_profile


async def _load_admin_operator_performance_rows(db) -> list[dict]:
    operator_docs = await db.users.aggregate(
        [
            {"$match": {"user_type": "operator"}},
            {"$addFields": {"_user_id_str": {"$toString": "$_id"}}},
            {
                "$lookup": {
                    "from": "operator_profiles",
                    "let": {"user_id_str": "$_user_id_str"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id_str"]}}},
                        {
                            "$project": {
                                "business_name": 1,
                                "description": 1,
                                "years_of_experience": 1,
                                "average_rating": 1,
                                "total_reviews": 1,
                                "specializations": 1,
                                "serving_areas": 1,
                            }
                        },
                    ],
                    "as": "profile_docs",
                }
            },
            {"$unwind": {"path": "$profile_docs", "preserveNullAndEmptyArrays": True}},
        ]
    ).to_list(length=None)

    profile_ids = [
        str(operator["profile_docs"]["_id"])
        for operator in operator_docs
        if operator.get("profile_docs") and operator["profile_docs"].get("_id")
    ]
    response_stats_by_profile = await _load_operator_response_stats(db, profile_ids)

    rows = []
    for operator in operator_docs:
        profile_doc = operator.get("profile_docs")
        profile_id = str(profile_doc["_id"]) if profile_doc and profile_doc.get("_id") else None
        average_rating = profile_doc.get("average_rating", 0) if profile_doc else 0
        response_stats = response_stats_by_profile.get(profile_id or "", {})

        row = {
            "_id": str(operator["_id"]),
            "email": operator.get("email"),
            "full_name": operator.get("full_name"),
            "phone": operator.get("phone"),
            "user_type": operator.get("user_type"),
            "is_active": operator.get("is_active", False),
            "created_at": operator.get("created_at"),
            "updated_at": operator.get("updated_at"),
            "profile": None,
            "serving_areas_count": 0,
            "avg_rating": average_rating,
            "total_responses": response_stats.get("total_responses", 0),
            "recent_responses_30d": response_stats.get("recent_responses_30d", 0),
            "avg_response_time_hours": response_stats.get("avg_response_time_hours", 0),
            "response_rate": round((average_rating / 5 * 100) if average_rating else 0, 2),
        }

        if profile_doc:
            row["profile"] = {
                "_id": profile_id,
                "business_name": profile_doc.get("business_name"),
                "description": profile_doc.get("description"),
                "years_of_experience": profile_doc.get("years_of_experience", 0),
                "average_rating": average_rating,
                "total_reviews": profile_doc.get("total_reviews", 0),
                "specializations": profile_doc.get("specializations", []),
                "serving_areas": profile_doc.get("serving_areas", []),
            }
            row["serving_areas_count"] = len(profile_doc.get("serving_areas", []))

        rows.append(row)

    return rows


def _sort_operator_performance_rows(rows: list[dict], sort_by: str) -> list[dict]:
    default_datetime = datetime.min.replace(tzinfo=timezone.utc)

    if sort_by == "responses":
        return sorted(
            rows,
            key=lambda row: (
                row.get("total_responses", 0),
                row.get("avg_rating", 0),
                _coerce_utc_datetime(row.get("created_at")) or default_datetime,
                row.get("_id", ""),
            ),
            reverse=True,
        )

    if sort_by == "response_time":
        return sorted(
            rows,
            key=lambda row: (
                row.get("avg_response_time_hours", 0) if row.get("total_responses", 0) else float("inf"),
                -(row.get("total_responses", 0)),
                -(row.get("avg_rating", 0)),
                row.get("_id", ""),
            ),
        )

    if sort_by == "experience":
        return sorted(
            rows,
            key=lambda row: (
                (row.get("profile") or {}).get("years_of_experience", 0),
                row.get("avg_rating", 0),
                row.get("total_responses", 0),
                _coerce_utc_datetime(row.get("created_at")) or default_datetime,
                row.get("_id", ""),
            ),
            reverse=True,
        )

    if sort_by == "specializations":
        return sorted(
            rows,
            key=lambda row: (
                len((row.get("profile") or {}).get("specializations", [])),
                row.get("avg_rating", 0),
                row.get("total_responses", 0),
                _coerce_utc_datetime(row.get("created_at")) or default_datetime,
                row.get("_id", ""),
            ),
            reverse=True,
        )

    return sorted(
        rows,
        key=lambda row: (
            row.get("avg_rating", 0),
            row.get("total_responses", 0),
            (row.get("profile") or {}).get("total_reviews", 0),
            _coerce_utc_datetime(row.get("created_at")) or default_datetime,
            row.get("_id", ""),
        ),
        reverse=True,
    )


async def _validate_location_promotion_payload(db, payload: dict, *, existing: dict | None = None):
    operator_profile_id = payload.get("operator_profile_id") or (existing or {}).get("operator_profile_id")

    try:
        operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(operator_profile_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operator_profile_id") from exc

    if not operator_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    scope = payload.get("location_scope") or (existing or {}).get("location_scope")
    if not scope:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="location_scope is required")

    if not _operator_supports_scope(operator_profile, scope):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator does not serve the requested promotion location",
        )

    service_type = payload.get("service_type") if "service_type" in payload else (existing or {}).get("service_type")
    if service_type and service_type not in operator_profile.get("service_types", ["tour"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator does not support the requested service type",
        )

    start_at = payload.get("start_at") if "start_at" in payload else (existing or {}).get("start_at")
    end_at = payload.get("end_at") if "end_at" in payload else (existing or {}).get("end_at")
    if start_at and end_at and end_at <= start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_at must be after start_at")

    return operator_profile


def _serialize_promotion(promotion: dict, *, operator_profile: dict | None = None) -> dict:
    promotion["_id"] = str(promotion["_id"])
    if operator_profile:
        promotion["operator_profile"] = {
            "_id": str(operator_profile["_id"]),
            "business_name": operator_profile.get("business_name"),
            "service_types": operator_profile.get("service_types", ["tour"]),
        }
    return promotion


async def get_token_from_header(authorization: str = Header(None)) -> str:
    """Extract and validate Bearer token from Authorization header"""
    if not authorization:
        logger.warning("Authorization header missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization format: {len(parts)} parts")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return parts[1]


def hash_password(password: str) -> str:
    """Hash password using shared app hasher (argon2)"""
    return get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using shared app hasher (argon2)"""
    return _verify_password(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token with expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_admin(request: Request, token: str = Depends(get_token_from_header)) -> dict:
    """
    Verify admin token and return admin data with full validation.
    
    Validation checks:
    - Token signature and expiration
    - Admin exists in database
    - Admin is active
    - Admin has valid role
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        principal_type = str(payload.get("principal_type") or "").casefold()
        if principal_type and principal_type != "admin":
            logger.warning("Token principal_type is not admin: %s", principal_type)
            raise credentials_exception

        admin_id: str = payload.get("sub")
        
        if admin_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        if not ObjectId.is_valid(admin_id):
            logger.warning("Token sub is not a valid admin id: %s", admin_id)
            raise credentials_exception
            
        # Check token expiration (redundant as jwt.decode validates, but explicit for clarity)
        exp: int = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            logger.warning(f"Token expired for admin: {admin_id}")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        raise credentials_exception
    
    db = await get_database()
    
    try:
        admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    except Exception as e:
        logger.error(f"Database error retrieving admin: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if admin is None:
        logger.warning(f"Admin not found: {admin_id}")
        raise credentials_exception
    
    # Check if admin is active
    if not admin.get("is_active"):
        logger.warning(f"Inactive admin attempted access: {admin_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive",
        )
    
    # Validate admin role
    admin_role = admin.get("role", "")
    if admin_role not in VALID_ADMIN_ROLES:
        logger.warning(f"Invalid admin role: {admin_role} for admin: {admin_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin role",
        )
    

    admin["_id"] = str(admin["_id"])
    request.state.admin = admin
    context = await ensure_admin_access_context(db, admin=admin)
    request.state.admin_access_context = context
    permission = required_permission_for_request(
        principal_type="admin",
        path=request.url.path,
        method=request.method,
    )
    if permission and not has_permission(set(context["permissions"]), permission):
        if settings.rbac_audit_decisions:
            await record_authorization_decision(
                db,
                principal_type="admin",
                principal_id=admin["_id"],
                principal_name=admin.get("full_name") or admin.get("email"),
                permission=permission,
                path=request.url.path,
                method=request.method,
                decision="denied",
                detail="Admin permission denied",
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin does not have access to this section")

    if settings.rbac_step_up_required and permission_requires_step_up(permission):
        max_age = settings.rbac_step_up_max_age_minutes
        if not is_recent_auth_payload(payload, max_age_minutes=max_age):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Re-authentication required for this sensitive action",
            )

    if permission and settings.rbac_audit_decisions:
        await record_authorization_decision(
            db,
            principal_type="admin",
            principal_id=admin["_id"],
            principal_name=admin.get("full_name") or admin.get("email"),
            permission=permission,
            path=request.url.path,
            method=request.method,
            decision="allowed",
        )
    return admin


async def get_current_admin_access_context(request: Request, admin: dict = Depends(get_current_admin)) -> dict:
    context = getattr(request.state, "admin_access_context", None)
    if context is None:
        db = await get_database()
        context = await ensure_admin_access_context(db, admin=admin)
        request.state.admin_access_context = context
    return context


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_admin(admin_data: AdminCreate, admin: dict = Depends(get_current_admin)):
    """
    Register a new admin (protected - requires super_admin role).
    Only super admins can create new admin accounts.
    """
    # Check if requesting admin has super_admin role
    if admin.get("role") != "super_admin":
        logger.warning(f"Unauthorized registration attempt by {admin.get('_id')} with role {admin.get('role')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can register new admins"
        )
    
    db = await get_database()
    
    # Validate email format
    if not admin_data.email or "@" not in admin_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Validate role
    if admin_data.role not in VALID_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ADMIN_ROLES)}"
        )
    
    # Validate password strength (minimum 8 characters)
    if len(admin_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if admin with this email already exists
    existing_admin = await db.admins.find_one({"email": admin_data.email})
    if existing_admin:
        logger.warning(f"Registration attempted with existing email: {admin_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email already exists"
        )
    
    # Hash password
    hashed_password = hash_password(admin_data.password)
    
    # Create admin document
    admin_doc = {
        "email": admin_data.email,
        "full_name": admin_data.full_name,
        "phone": admin_data.phone,
        "role": admin_data.role,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None,
        "created_by": admin.get("_id")  # Track who created this admin
    }
    
    try:
        result = await db.admins.insert_one(admin_doc)
        logger.info(f"New admin created: {result.inserted_id} by {admin.get('_id')}")
        
        return {
            "message": "Admin registered successfully",
            "admin_id": str(result.inserted_id),
            "role": admin_data.role
        }
    except Exception as e:
        logger.error(f"Error creating admin: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
async def admin_login(credentials: AdminLogin, request: Request):
    """
    Admin login endpoint with security logging.
    Returns access token with 8-hour expiration and admin info.
    Failed attempts are logged for security auditing.
    """
    db = await get_database()
    
    email = credentials.email.strip().casefold()
    admin = await db.admins.find_one({"email": email})
    
    if not admin:
        logger.warning(f"Login attempt with non-existent email: {credentials.email}")
        await record_login_security_event(
            db,
            principal_type="admin",
            email=email,
            outcome="invalid_credentials",
            ip_address=_request_ip(request),
            location="Admin Console",
            user_name=email,
            description=f"Invalid admin credentials for {email}",
            threshold_enabled=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not admin.get("is_active"):
        logger.warning(f"Login attempt by inactive admin: {admin.get('_id')}")
        await record_login_security_event(
            db,
            principal_type="admin",
            email=email,
            outcome="inactive_account",
            ip_address=_request_ip(request),
            location="Admin Console",
            user_name=admin.get("full_name") or email,
            user_id=str(admin.get("_id")),
            description=f"Login attempt against inactive admin account {email}",
            remediation="Review admin status before retrying authentication.",
            threshold_enabled=False,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    if not verify_password(credentials.password, admin.get("hashed_password", "")):
        logger.warning(f"Failed login attempt for admin: {admin.get('_id')}")
        await record_login_security_event(
            db,
            principal_type="admin",
            email=email,
            outcome="invalid_credentials",
            ip_address=_request_ip(request),
            location="Admin Console",
            user_name=admin.get("full_name") or email,
            user_id=str(admin.get("_id")),
            description=f"Invalid admin credentials for {email}",
            threshold_enabled=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login timestamp
    try:
        await db.admins.update_one(
            {"_id": admin["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        logger.info(f"Successful login for admin: {admin.get('_id')}")
    except Exception as e:
        logger.error(f"Error updating last_login: {str(e)}")

    await record_login_security_event(
        db,
        principal_type="admin",
        email=email,
        outcome="success",
        ip_address=_request_ip(request),
        location="Admin Console",
        user_name=admin.get("full_name") or email,
        user_id=str(admin.get("_id")),
        description=f"Successful admin login for {email}",
        threshold_enabled=False,
    )
    
    access_context = await ensure_admin_access_context(db, admin=admin)

    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(admin["_id"]),
            "principal_type": "admin",
            "admin_role": admin.get("role"),
            "organization_id": access_context["organization"]["_id"],
            "role_keys": access_context["membership"].get("role_keys", []),
        }
    )
    
    admin["_id"] = str(admin["_id"])
    
    return AdminToken(
        access_token=access_token,
        token_type="bearer",
        admin=Admin(**admin)
    )


@router.get("/profile")
async def get_admin_profile(admin: dict = Depends(get_current_admin)):
    """Get current admin profile"""
    return Admin(**admin)


@router.put("/profile")
async def update_admin_profile(
    updates: dict,
    admin: dict = Depends(get_current_admin)
):
    """Update admin profile"""
    db = await get_database()
    
    # Only allow certain fields to be updated
    allowed_fields = {"full_name", "phone"}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.admins.update_one(
        {"_id": ObjectId(admin["_id"])},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}


@router.post("/change-password")
async def change_admin_password(
    old_password: str,
    new_password: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Change admin password with validation.
    Requires old password for verification and enforces minimum length.
    """
    db = await get_database()
    
    # Verify old password
    if not verify_password(old_password, admin.get("hashed_password", "")):
        logger.warning(f"Failed password change attempt for admin: {admin.get('_id')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    # Prevent reusing same password
    if verify_password(new_password, admin.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password"
        )
    
    # Hash new password
    hashed_password = hash_password(new_password)
    
    try:
        await db.admins.update_one(
            {"_id": ObjectId(admin["_id"])},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info(f"Password changed for admin: {admin.get('_id')}")
        return {"message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= DASHBOARD ENDPOINTS =============

@router.get("/dashboard/stats")
async def get_dashboard_stats(admin: dict = Depends(get_current_admin)):
    """Get main dashboard statistics"""
    db = await get_database()
    
    # Count total users
    total_tourists = await db.users.count_documents({"user_type": "tourist"})
    total_operators = await db.users.count_documents({"user_type": "operator"})
    total_users = total_tourists + total_operators
    
    # Active users (logged in last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = await db.users.count_documents({"last_login": {"$gte": seven_days_ago}})
    
    # Quote statistics
    total_quotes = await db.quote_requests.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})
    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    
    # Total responses
    total_responses = 0
    async for quote in db.quote_requests.find({}):
        total_responses += len(quote.get("responses", []))
    
    # Calculate conversion rate
    conversion_rate = ((total_responses / total_quotes) * 100) if total_quotes > 0 else 0
    
    # Average responses per quote
    avg_responses_per_quote = (total_responses / total_quotes) if total_quotes > 0 else 0
    
    # Operator statistics
    total_operator_profiles = await db.operator_profiles.count_documents({})
    total_tickets = await db.support_tickets.count_documents({})
    open_tickets = await db.support_tickets.count_documents({"status": {"$in": ["open", "acknowledged", "in_progress"]}})
    completed_tickets = await db.support_tickets.count_documents({"status": "completed"})
    
    # Get average operator rating
    pipeline = [
        {"$group": {"_id": None, "avg_rating": {"$avg": "$average_rating"}}}
    ]
    rating_result = await db.operator_profiles.aggregate(pipeline).to_list(1)
    avg_operator_rating = rating_result[0]["avg_rating"] if rating_result else 0
    
    return {
        "users": {
            "total": total_users,
            "tourists": total_tourists,
            "operators": total_operators,
            "active_last_7_days": active_users
        },
        "quotes": {
            "total": total_quotes,
            "open": open_quotes,
            "closed": closed_quotes,
            "total_responses": total_responses,
            "conversion_rate": round(conversion_rate, 2),
            "avg_responses_per_quote": round(avg_responses_per_quote, 2)
        },
        "operators": {
            "total_profiles": total_operator_profiles,
            "avg_rating": round(avg_operator_rating, 2)
        },
        "tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "completed": completed_tickets,
        }
    }


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(admin: dict = Depends(get_current_admin)):
    """Get detailed metrics for charts"""
    db = await get_database()
    
    # User registration trend (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pipeline_users = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "user_type": "$user_type"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    user_growth = await db.users.aggregate(pipeline_users).to_list(None)
    
    # Quote trend (last 30 days)
    pipeline_quotes = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    quote_trend = await db.quote_requests.aggregate(pipeline_quotes).to_list(None)
    
    # Top destinations (most requested)
    pipeline_destinations = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.name",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_destinations = await db.quote_requests.aggregate(pipeline_destinations).to_list(None)
    
    # Top states
    pipeline_states = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.state",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_states = await db.quote_requests.aggregate(pipeline_states).to_list(None)
    
    return {
        "user_growth": [
            {
                "date": item["_id"]["date"],
                "tourists": next((x["count"] for x in user_growth if x["_id"]["date"] == item["_id"]["date"] and x["_id"]["user_type"] == "tourist"), 0),
                "operators": next((x["count"] for x in user_growth if x["_id"]["date"] == item["_id"]["date"] and x["_id"]["user_type"] == "operator"), 0)
            }
            for item in user_growth if "date" in item["_id"]
        ],
        "quote_trend": [
            {
                "date": item["_id"],
                "count": item["count"]
            }
            for item in quote_trend
        ],
        "top_destinations": [
            {
                "name": item["_id"],
                "count": item["count"]
            }
            for item in top_destinations
        ],
        "top_states": [
            {
                "name": item["_id"],
                "count": item["count"]
            }
            for item in top_states
        ]
    }


@router.get("/dashboard/response-times")
async def get_response_times(admin: dict = Depends(get_current_admin)):
    """Get operator response time analytics"""
    db = await get_database()
    
    response_times = []
    
    # Iterate through quotes with responses
    async for quote in db.quote_requests.find({"responses": {"$exists": True, "$not": {"$size": 0}}}):
        quote_created = quote.get("created_at")
        for response in quote.get("responses", []):
            response_time = response.get("created_at", quote_created)
            if quote_created and response_time:
                time_diff_hours = (response_time - quote_created).total_seconds() / 3600
                response_times.append(time_diff_hours)
    
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        median_response_time = sorted(response_times)[len(response_times) // 2]
    else:
        avg_response_time = min_response_time = max_response_time = median_response_time = 0
    
    return {
        "average_hours": round(avg_response_time, 2),
        "minimum_hours": round(min_response_time, 2),
        "maximum_hours": round(max_response_time, 2),
        "median_hours": round(median_response_time, 2),
        "total_responses_analyzed": len(response_times)
    }


# ============= USER MANAGEMENT ENDPOINTS =============

@router.get("/tourists")
async def get_all_tourists(
    limit: int = 50,
    cursor: str | None = None,
    search: str = "",
    status_filter: str | None = None,
    admin: dict = Depends(get_current_admin)
):
    """Get all tourists with pagination and search"""
    db = await get_database()
    
    # Build search query
    query = {"user_type": "tourist"}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    if status_filter == "active":
        query["is_active"] = True
    elif status_filter == "inactive":
        query["is_active"] = False
    
    # Get total count
    total = await db.users.count_documents(query)
    
    cursor_match = None
    if cursor:
        cursor_created_at, cursor_document_id = _decode_datetime_object_cursor(cursor)
        cursor_match = {
            "$or": [
                {"created_at": {"$lt": cursor_created_at}},
                {"created_at": cursor_created_at, "_id": {"$lt": cursor_document_id}},
            ]
        }

    effective_query = dict(query)
    if cursor_match:
        effective_query["$and"] = [cursor_match]

    tourist_docs = await db.users.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(limit + 1).to_list(length=limit + 1)
    has_more = len(tourist_docs) > limit
    tourist_docs = tourist_docs[:limit]
    tourist_ids = [str(tourist["_id"]) for tourist in tourist_docs]
    quote_counts = await db.quote_requests.aggregate(
        [
            {"$match": {"tourist_id": {"$in": tourist_ids}}},
            {"$group": {"_id": "$tourist_id", "count": {"$sum": 1}}},
        ]
    ).to_list(length=None)
    quote_count_by_tourist = {row["_id"]: row["count"] for row in quote_counts}

    tourists = []
    for tourist in tourist_docs:
        tourist["_id"] = str(tourist["_id"])
        tourist["quotes_posted"] = quote_count_by_tourist.get(tourist["_id"], 0)
        tourists.append(tourist)

    next_cursor = None
    if has_more and tourist_docs:
        last_tourist = tourist_docs[-1]
        next_cursor = _encode_datetime_object_cursor(created_at=last_tourist["created_at"], document_id=last_tourist["_id"])

    total_pages = max(1, (total + limit - 1) // limit)
    
    return {
        "tourists": tourists,
        "pagination": {
            "page_size": limit,
            "total_items": total,
            "total_pages": total_pages,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
    }


@router.get("/operators")
async def get_all_operators(
    limit: int = 50,
    cursor: str | None = None,
    search: str = "",
    rating_filter: str = "",
    admin: dict = Depends(get_current_admin)
):
    """Get all operators with pagination and search"""
    db = await get_database()
    
    # Build search query for operators
    base_query = {"user_type": "operator"}
    base_query_filters = []
    if search:
        base_query_filters.append({"$or": [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]})
    if base_query_filters:
        base_query["$and"] = base_query_filters

    paged_query = dict(base_query)
    paged_query_filters = list(base_query_filters)
    if cursor:
        cursor_created_at, cursor_document_id = _decode_datetime_object_cursor(cursor)
        paged_query_filters.append({"$or": [
            {"created_at": {"$lt": cursor_created_at}},
            {"created_at": cursor_created_at, "_id": {"$lt": cursor_document_id}},
        ]})
    if paged_query_filters:
        paged_query["$and"] = paged_query_filters

    base_operator_pipeline = [
        {"$match": base_query},
        {"$addFields": {"_user_id_str": {"$toString": "$_id"}}},
        {
            "$lookup": {
                "from": "operator_profiles",
                "let": {"user_id_str": "$_user_id_str"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id_str"]}}},
                    {
                        "$project": {
                            "business_name": 1,
                            "description": 1,
                            "years_of_experience": 1,
                            "average_rating": 1,
                            "total_reviews": 1,
                            "specializations": 1,
                            "serving_areas": 1,
                        }
                    },
                ],
                "as": "profile_docs",
            }
        },
        {"$unwind": {"path": "$profile_docs", "preserveNullAndEmptyArrays": True}},
    ]

    operator_pipeline = [{"$match": paged_query}, *base_operator_pipeline[1:]]

    rating_match = None
    if rating_filter == "4":
        rating_match = {"profile_docs.average_rating": {"$gte": 4}}
    elif rating_filter == "3":
        rating_match = {"profile_docs.average_rating": {"$gte": 3, "$lt": 4}}
    elif rating_filter == "below3":
        rating_match = {"$or": [{"profile_docs.average_rating": {"$lt": 3}}, {"profile_docs.average_rating": {"$exists": False}}]}

    if rating_match:
        base_operator_pipeline.append({"$match": rating_match})
        operator_pipeline.append({"$match": rating_match})

    total_rows = await db.users.aggregate(base_operator_pipeline + [{"$count": "total"}]).to_list(length=1)
    total = total_rows[0]["total"] if total_rows else 0

    operator_docs = await db.users.aggregate(
        operator_pipeline
        + [
            {"$sort": {"created_at": -1, "_id": -1}},
            {"$limit": limit + 1},
        ]
    ).to_list(length=limit + 1)

    has_more = len(operator_docs) > limit
    visible_operator_docs = operator_docs[:limit]

    profile_ids = [str(operator["profile_docs"]["_id"]) for operator in visible_operator_docs if operator.get("profile_docs") and operator["profile_docs"].get("_id")]
    response_counts = await db.quote_requests.aggregate(
        [
            {"$unwind": "$responses"},
            {"$match": {"responses.operator_id": {"$in": profile_ids}}},
            {"$group": {"_id": "$responses.operator_id", "count": {"$sum": 1}}},
        ]
    ).to_list(length=None)
    response_count_by_operator = {row["_id"]: row["count"] for row in response_counts}

    operators = []
    for operator in visible_operator_docs:
        profile_doc = operator.get("profile_docs")
        operator_id = str(operator["_id"])
        profile_id = str(profile_doc["_id"]) if profile_doc and profile_doc.get("_id") else None
        operator["_id"] = operator_id
        operator["profile"] = None
        operator["serving_areas_count"] = 0
        operator["quotes_responded"] = 0
        operator["avg_rating"] = 0

        if profile_doc:
            operator["profile"] = {
                "_id": profile_id,
                "business_name": profile_doc.get("business_name"),
                "description": profile_doc.get("description"),
                "years_of_experience": profile_doc.get("years_of_experience"),
                "average_rating": profile_doc.get("average_rating", 0),
                "total_reviews": profile_doc.get("total_reviews", 0),
                "specializations": profile_doc.get("specializations", []),
            }
            operator["serving_areas_count"] = len(profile_doc.get("serving_areas", []))
            operator["avg_rating"] = profile_doc.get("average_rating", 0)
            operator["quotes_responded"] = response_count_by_operator.get(profile_id, 0)

        operator.pop("profile_docs", None)
        operator.pop("_user_id_str", None)
        operators.append(operator)

    total_pages = max(1, math.ceil(total / limit)) if limit else 1
    next_cursor = None
    if has_more and visible_operator_docs:
        last_operator = visible_operator_docs[-1]
        next_cursor = _encode_datetime_object_cursor(
            created_at=last_operator["created_at"],
            document_id=last_operator["_id"],
        )
    
    return {
        "operators": operators,
        "total": total,
        "pagination": {
            "page_size": limit,
            "total_items": total,
            "total_pages": total_pages,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
    }


@router.post("/promotions/location", status_code=status.HTTP_201_CREATED)
async def create_location_promotion(
    promotion: LocationPromotionCreate,
    admin: dict = Depends(get_current_admin),
):
    """Create a location-scoped promotion campaign for an operator profile."""
    db = await get_database()
    payload = promotion.model_dump()
    operator_profile = await _validate_location_promotion_payload(db, payload)

    normalized_scope = _build_normalized_location_scope(payload["location_scope"])
    now = datetime.now(timezone.utc)
    status_value = payload.get("status", "draft")

    promotion_doc = {
        **payload,
        "normalized_location_scope": normalized_scope,
        "approved_by": admin.get("_id") if status_value == "active" else None,
        "approved_at": now if status_value == "active" else None,
        "last_daily_reset_at": now,
        "total_impressions": 0,
        "total_clicks": 0,
        "last_served_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.location_promotions.insert_one(promotion_doc)
    promotion_doc["_id"] = result.inserted_id

    return {
        "message": "Location promotion created successfully",
        "promotion": _serialize_promotion(promotion_doc, operator_profile=operator_profile),
    }


@router.get("/promotions/location")
async def list_location_promotions(
    status_filter: str | None = None,
    area_name: str | None = None,
    service_type: str | None = None,
    admin: dict = Depends(get_current_admin),
):
    """List location-scoped promotion campaigns."""
    db = await get_database()
    query = {}
    if status_filter:
        query["status"] = status_filter
    if area_name:
        query["normalized_location_scope.area_name"] = _normalize_location_value(area_name)
    if service_type:
        query["service_type"] = service_type

    promotions = []
    cursor = db.location_promotions.find(query).sort([("updated_at", -1), ("priority", -1)])
    async for promotion in cursor:
        operator_profile = None
        operator_profile_id = promotion.get("operator_profile_id")
        if operator_profile_id:
            try:
                operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(operator_profile_id)})
            except Exception:
                operator_profile = None
        promotions.append(_serialize_promotion(promotion, operator_profile=operator_profile))

    return {"promotions": promotions, "count": len(promotions)}


@router.patch("/promotions/location/{promotion_id}")
async def update_location_promotion(
    promotion_id: str,
    updates: LocationPromotionUpdate,
    admin: dict = Depends(get_current_admin),
):
    """Update a location-scoped promotion campaign."""
    db = await get_database()
    try:
        existing = await db.location_promotions.find_one({"_id": ObjectId(promotion_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid promotion ID") from exc

    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    update_data = {key: value for key, value in updates.model_dump().items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")

    operator_profile = await _validate_location_promotion_payload(db, update_data, existing=existing)

    if "location_scope" in update_data:
        update_data["normalized_location_scope"] = _build_normalized_location_scope(update_data["location_scope"])

    if update_data.get("status") == "active" and existing.get("status") != "active":
        update_data["approved_by"] = admin.get("_id")
        update_data["approved_at"] = datetime.now(timezone.utc)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.location_promotions.update_one(
        {"_id": ObjectId(promotion_id)},
        {"$set": update_data},
    )

    updated = await db.location_promotions.find_one({"_id": ObjectId(promotion_id)})
    return {
        "message": "Location promotion updated successfully",
        "promotion": _serialize_promotion(updated, operator_profile=operator_profile),
    }


@router.delete("/promotions/location/{promotion_id}")
async def delete_location_promotion(
    promotion_id: str,
    admin: dict = Depends(get_current_admin),
):
    """Delete a location-scoped promotion campaign."""
    db = await get_database()
    try:
        result = await db.location_promotions.delete_one({"_id": ObjectId(promotion_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid promotion ID") from exc

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    return {"message": "Location promotion deleted successfully"}


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Suspend a user account"""
    db = await get_database()
    
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"message": "User suspended successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error suspending user: {str(e)}"
        )


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Activate a suspended user account"""
    db = await get_database()
    
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"message": "User activated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error activating user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Delete a user account"""
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user
        await db.users.delete_one({"_id": ObjectId(user_id)})
        
        # If operator, also delete operator profile
        if user.get("user_type") == "operator":
            await db.operator_profiles.delete_one({"user_id": user_id})
        
        return {"message": "User deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting user: {str(e)}"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed information about a user"""
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user["_id"] = str(user["_id"])
        user.pop("hashed_password", None)  # Don't expose password
        
        # Add additional info based on user type
        if user.get("user_type") == "tourist":
            quotes = []
            cursor = db.quote_requests.find({"tourist_id": user["_id"]}).sort("created_at", -1)
            async for quote in cursor:
                quote["_id"] = str(quote["_id"])
                quotes.append(quote)
            user["quotes"] = quotes
            
        elif user.get("user_type") == "operator":
            profile = await db.operator_profiles.find_one({"user_id": user["_id"]})
            if profile:
                profile["_id"] = str(profile["_id"])
                user["profile"] = profile
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching user: {str(e)}"
        )


# ============= QUOTE MANAGEMENT ENDPOINTS =============

@router.get("/quotes")
async def get_all_quotes(
    limit: int = 50,
    cursor: str = None,
    status_filter: str = None,
    response_filter: str = None,
    search: str = "",
    admin: dict = Depends(get_current_admin)
):
    """Get all quotes with pagination, filtering and search"""
    db = await get_database()
    
    query = {}
    
    # Filter by status
    if status_filter and status_filter in ["open", "closed"]:
        query["status"] = status_filter

    if response_filter == "0":
        query["responses.0"] = {"$exists": False}
    elif response_filter == "1plus":
        query["responses.0"] = {"$exists": True}
    elif response_filter == "5plus":
        query["responses.4"] = {"$exists": True}
    
    # Search by tourist name or location
    if search:
        query["$or"] = [
            {"tourist_name": {"$regex": search, "$options": "i"}},
            {"tourist_email": {"$regex": search, "$options": "i"}},
            {"from_location": {"$regex": search, "$options": "i"}},
            {"to_location": {"$regex": search, "$options": "i"}},
            {"locations.name": {"$regex": search, "$options": "i"}},
            {"locations.state": {"$regex": search, "$options": "i"}},
            {"locations.country": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.quote_requests.count_documents(query)

    cursor_match = None
    if cursor:
        cursor_created_at, cursor_document_id = _decode_datetime_object_cursor(cursor)
        cursor_match = {
            "$or": [
                {"created_at": {"$lt": cursor_created_at}},
                {"created_at": cursor_created_at, "_id": {"$lt": cursor_document_id}},
            ]
        }

    effective_query = dict(query)
    if cursor_match:
        effective_query["$and"] = [cursor_match]
    
    quotes = []
    quote_docs = await db.quote_requests.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(limit + 1).to_list(length=limit + 1)
    has_more = len(quote_docs) > limit
    quote_docs = quote_docs[:limit]
    for quote in quote_docs:
        quote["_id"] = str(quote["_id"])
        if "tourist_id" in quote:
            quote["tourist_id"] = str(quote["tourist_id"])
        
        # Add response count
        quote["total_responses"] = len(quote.get("responses", []))
        quote["responses_count"] = quote["total_responses"]
        quote["is_closed"] = quote.get("status") == "closed"
        quotes.append(quote)

    next_cursor = None
    if has_more and quote_docs:
        last_quote = quote_docs[-1]
        next_cursor = _encode_datetime_object_cursor(created_at=last_quote["created_at"], document_id=last_quote["_id"])

    total_pages = max(1, (total + limit - 1) // limit)
    
    return {
        "quotes": quotes,
        "pagination": {
            "page_size": limit,
            "total_items": total,
            "total_pages": total_pages,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
    }


@router.get("/quotes/stats")
async def get_quotes_stats(admin: dict = Depends(get_current_admin)):
    """Get quote analytics and statistics"""
    db = await get_database()
    
    # Status breakdown
    total_quotes = await db.quote_requests.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})
    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    
    # Quotes by state
    pipeline_states = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.state",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ]
    quotes_by_state = await db.quote_requests.aggregate(pipeline_states).to_list(None)
    
    # Quotes by country
    pipeline_countries = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.country",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ]
    quotes_by_country = await db.quote_requests.aggregate(pipeline_countries).to_list(None)
    
    # Average quote budget (if available)
    pipeline_budget = [
        {"$group": {
            "_id": None,
            "avg_budget": {"$avg": "$budget"},
            "min_budget": {"$min": "$budget"},
            "max_budget": {"$max": "$budget"}
        }}
    ]
    budget_stats = await db.quote_requests.aggregate(pipeline_budget).to_list(1)
    
    return {
        "status_breakdown": {
            "total": total_quotes,
            "open": open_quotes,
            "closed": closed_quotes
        },
        "by_state": [
            {"name": item["_id"], "count": item["count"]}
            for item in quotes_by_state
        ],
        "by_country": [
            {"name": item["_id"], "count": item["count"]}
            for item in quotes_by_country
        ],
        "budget_stats": budget_stats[0] if budget_stats else {}
    }


@router.get("/quotes/{quote_id}")
async def get_quote_details(
    quote_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed information about a quote"""
    db = await get_database()
    
    try:
        quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        quote["_id"] = str(quote["_id"])
        if "tourist_id" in quote:
            quote["tourist_id"] = str(quote["tourist_id"])
        
        # Get tourist details
        tourist = await db.users.find_one({"_id": ObjectId(quote["tourist_id"])})
        if tourist:
            tourist["_id"] = str(tourist["_id"])
            tourist.pop("hashed_password", None)
            quote["tourist_details"] = tourist
        
        # Get operator details for each response
        for response in quote.get("responses", []):
            operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(response.get("operator_id", "0"))})
            if operator_profile:
                response["operator_profile"] = {
                    "_id": str(operator_profile["_id"]),
                    "business_name": operator_profile.get("business_name"),
                    "average_rating": operator_profile.get("average_rating")
                }
        
        return quote
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching quote: {str(e)}"
        )


# ============= OPERATOR PERFORMANCE ENDPOINTS =============

@router.get("/operators/performance")
async def get_operators_performance(
    limit: int = 50,
    sort_by: str = "rating",
    admin: dict = Depends(get_current_admin)
):
    """Get operator performance metrics"""
    db = await get_database()
    all_rows = _sort_operator_performance_rows(await _load_admin_operator_performance_rows(db), sort_by)
    operators = all_rows[:limit]

    return {
        "operators": operators,
        "total": len(all_rows),
        "limit": limit
    }


@router.get("/operators/leaderboard")
async def get_operators_leaderboard(
    metric: str = "rating",
    limit: int = 10,
    admin: dict = Depends(get_current_admin)
):
    """Get operator leaderboard by various metrics"""
    db = await get_database()
    leaderboard = _sort_operator_performance_rows(await _load_admin_operator_performance_rows(db), metric)[:limit]
    for index, operator in enumerate(leaderboard, start=1):
        operator["rank"] = index

    return {
        "metric": metric,
        "leaderboard": leaderboard,
        "operators": leaderboard,
    }


@router.get("/operators/{operator_id}/performance")
async def get_operator_performance_details(
    operator_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed performance analytics for a specific operator"""
    db = await get_database()
    
    try:
        operator = await db.operator_profiles.find_one({"_id": ObjectId(operator_id)})
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operator not found"
            )
        
        operator["_id"] = str(operator["_id"])

        response_stats = await _load_operator_response_stats(db, [str(operator["_id"])])
        operator_stats = response_stats.get(str(operator["_id"]), {})
        total_responses = operator_stats.get("total_responses", 0)
        avg_response_time = operator_stats.get("avg_response_time_hours", 0)
        specializations_count = {
            spec: total_responses for spec in operator.get("specializations", [])
        }
        
        return {
            "operator": operator,
            "performance": {
                "total_responses": total_responses,
                "average_response_time_hours": avg_response_time,
                "average_rating": operator.get("average_rating", 0),
                "total_reviews": operator.get("total_reviews", 0),
                "specializations": specializations_count,
                "serving_areas_count": len(operator.get("serving_areas", []))
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching operator performance: {str(e)}"
        )


# ============= FINANCIAL MANAGEMENT ENDPOINTS =============

@router.get("/financial/overview")
async def get_financial_overview(admin: dict = Depends(get_current_admin)):
    """Get financial overview metrics for admin dashboard."""
    db = await get_database()

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    commission_percentage = 15

    completed_stats_rows = await db.bookings.aggregate(
        [
            {"$match": {"booking_status.status": "completed"}},
            {
                "$project": {
                    "amount": {"$ifNull": ["$final_cost", "$estimated_cost"]},
                    "created_at": 1,
                }
            },
            {"$match": {"amount": {"$gt": 0}}},
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$amount"},
                    "transaction_count": {"$sum": 1},
                    "monthly_revenue": {
                        "$sum": {
                            "$cond": [{"$gte": ["$created_at", month_start]}, "$amount", 0]
                        }
                    },
                }
            },
        ]
    ).to_list(length=1)
    completed_stats = completed_stats_rows[0] if completed_stats_rows else {}

    total_revenue = float(completed_stats.get("total_revenue", 0) or 0)
    transaction_count = int(completed_stats.get("transaction_count", 0) or 0)
    monthly_revenue = float(completed_stats.get("monthly_revenue", 0) or 0)
    avg_transaction = (total_revenue / transaction_count) if transaction_count else 0
    commission_collected = total_revenue * (commission_percentage / 100)
    processing_fees = total_revenue * 0.02

    pending_rows = await db.bookings.aggregate(
        [
            {"$match": {"booking_status.status": {"$in": ["pending", "confirmed"]}, "operator_id": {"$exists": True, "$ne": None}}},
            {
                "$project": {
                    "operator_id": 1,
                    "payable": {
                        "$multiply": [
                            {"$ifNull": ["$final_cost", "$estimated_cost"]},
                            1 - commission_percentage / 100,
                        ]
                    },
                }
            },
            {"$match": {"payable": {"$gt": 0}}},
            {"$group": {"_id": "$operator_id", "amount": {"$sum": "$payable"}}},
        ]
    ).to_list(length=None)

    pending_payouts = sum(float(row.get("amount", 0) or 0) for row in pending_rows)
    pending_payout_count = len(pending_rows)

    return {
        "totalRevenue": round(total_revenue, 2),
        "monthlyRevenue": round(monthly_revenue, 2),
        "pendingPayouts": round(pending_payouts, 2),
        "pendingPayoutCount": pending_payout_count,
        "commissionCollected": round(commission_collected, 2),
        "commissionPercentage": commission_percentage,
        "processingFees": round(processing_fees, 2),
        "avgTransaction": round(avg_transaction, 2),
    }


@router.get("/financial/transactions")
async def get_financial_transactions(admin: dict = Depends(get_current_admin)):
    """Get transaction-style records derived from bookings."""
    db = await get_database()

    method_cycle = ["card", "upi", "wallet"]
    commission_rate = 15

    booking_docs = await db.bookings.find(
        {
            "$or": [
                {"final_cost": {"$gt": 0}},
                {"estimated_cost": {"$gt": 0}},
            ]
        },
        {"tourist_id": 1, "operator_id": 1, "final_cost": 1, "estimated_cost": 1, "updated_at": 1, "created_at": 1, "booking_status": 1},
    ).sort("created_at", -1).to_list(length=None)

    tourist_ids = {booking.get("tourist_id") for booking in booking_docs if booking.get("tourist_id")}
    operator_ids = {booking.get("operator_id") for booking in booking_docs if booking.get("operator_id")}
    users_by_id = await _load_users_by_id(db, tourist_ids)
    profiles_by_id = await _load_operator_profiles_by_id(db, operator_ids)

    transactions = []
    for booking in booking_docs:
        booking_id = str(booking.get("_id"))
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if not amount or amount <= 0:
            continue

        tourist = users_by_id.get(booking.get("tourist_id"), {})
        operator_profile = profiles_by_id.get(booking.get("operator_id"), {})

        method = method_cycle[sum(ord(c) for c in booking_id) % len(method_cycle)]
        status_map = {
            "completed": "completed",
            "pending": "pending",
            "confirmed": "pending",
            "cancelled": "failed",
        }

        transactions.append(
            {
                "_id": booking_id,
                "transaction_id": f"TXN-{booking_id[-8:].upper()}",
                "date": booking.get("updated_at") or booking.get("created_at"),
                "tourist_name": tourist.get("full_name", "Unknown Tourist"),
                "operator_name": operator_profile.get("business_name", "Unknown Operator"),
                "amount": round(float(amount), 2),
                "commission": round(float(amount) * (commission_rate / 100), 2),
                "commission_rate": commission_rate,
                "method": method,
                "status": status_map.get(booking.get("booking_status", {}).get("status"), "pending"),
            }
        )

    return {"transactions": transactions}


@router.get("/financial/commissions")
async def get_financial_commissions(admin: dict = Depends(get_current_admin)):
    """Get per-operator commission summary for the current period."""
    db = await get_database()

    commission_rate = 15
    rows = await db.bookings.aggregate(
        [
            {"$match": {"booking_status.status": {"$in": ["completed", "confirmed"]}, "operator_id": {"$exists": True, "$ne": None}}},
            {"$project": {"operator_id": 1, "amount": {"$ifNull": ["$final_cost", "$estimated_cost"]}}},
            {"$match": {"amount": {"$gt": 0}}},
            {"$group": {"_id": "$operator_id", "gross_amount": {"$sum": "$amount"}}},
        ]
    ).to_list(length=None)
    profiles_by_id = await _load_operator_profiles_by_id(db, [row["_id"] for row in rows if row.get("_id")])

    current_period = datetime.now(timezone.utc).strftime("%b %Y")
    commissions = []
    for row in rows:
        operator_id = row.get("_id")
        earned = float(row.get("gross_amount", 0)) * (commission_rate / 100)
        commissions.append(
            {
                "_id": f"{operator_id}-{current_period}",
                "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                "period": current_period,
                "earned": round(earned, 2),
                "adjustments": 0,
                "net": round(earned, 2),
                "status": "settled",
            }
        )

    commissions.sort(key=lambda c: c["earned"], reverse=True)
    return {"commissions": commissions}


@router.get("/financial/payouts")
async def get_financial_payouts(admin: dict = Depends(get_current_admin)):
    """Get pending payouts and payout history derived from booking state."""
    db = await get_database()

    commission_rate = 15
    pending_rows = await db.bookings.aggregate(
        [
            {"$match": {"booking_status.status": {"$in": ["pending", "confirmed"]}, "operator_id": {"$exists": True, "$ne": None}}},
            {
                "$project": {
                    "operator_id": 1,
                    "payable": {"$multiply": [{"$ifNull": ["$final_cost", "$estimated_cost"]}, 1 - commission_rate / 100]},
                    "activity_at": {"$ifNull": ["$updated_at", "$created_at"]},
                }
            },
            {"$match": {"payable": {"$gt": 0}}},
            {"$group": {"_id": "$operator_id", "amount": {"$sum": "$payable"}, "latest_date": {"$max": "$activity_at"}}},
        ]
    ).to_list(length=None)

    history_bookings = await db.bookings.find(
        {"booking_status.status": "completed", "$or": [{"final_cost": {"$gt": 0}}, {"estimated_cost": {"$gt": 0}}]},
        {"operator_id": 1, "final_cost": 1, "estimated_cost": 1, "updated_at": 1, "created_at": 1},
    ).sort("updated_at", -1).limit(50).to_list(length=50)

    profile_ids = {row.get("_id") for row in pending_rows if row.get("_id")}
    profile_ids.update({booking.get("operator_id") for booking in history_bookings if booking.get("operator_id")})
    profiles_by_id = await _load_operator_profiles_by_id(db, profile_ids)

    history = []
    for booking in history_bookings:
        operator_id = booking.get("operator_id")
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        payable = float(amount) * (1 - commission_rate / 100)
        booking_id = str(booking.get("_id"))
        history.append(
            {
                "_id": booking_id,
                "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                "date": booking.get("updated_at") or booking.get("created_at"),
                "amount": round(payable, 2),
                "status": "completed",
                "reference_id": f"PAY-{booking_id[-8:].upper()}",
            }
        )

    pending = []
    now = datetime.now(timezone.utc)
    for row in pending_rows:
        operator_id = row.get("_id")
        amount = float(row.get("amount", 0))
        if amount <= 0:
            continue

        latest = _coerce_utc_datetime(row.get("latest_date")) or now
        days_pending = max((now - latest).days, 0)
        pending.append(
            {
                "_id": operator_id,
                "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                "amount": round(amount, 2),
                "daysPending": days_pending,
                "bankName": "N/A",
                "accountLast4": "0000",
            }
        )

    pending.sort(key=lambda p: p["amount"], reverse=True)
    return {
        "pending": pending,
        "history": history[:50],
    }


@router.get("/financial/reports")
async def get_financial_reports(admin: dict = Depends(get_current_admin)):
    """Get generated report metadata and scheduled exports."""
    now = datetime.now(timezone.utc)
    generated = [
        {
            "_id": "report-revenue-latest",
            "name": f"Revenue Report - {now.strftime('%b %Y')}",
            "generated_at": now,
        },
        {
            "_id": "report-commission-latest",
            "name": f"Commission Breakdown - {now.strftime('%b %Y')}",
            "generated_at": now - timedelta(days=1),
        },
    ]

    scheduled = [
        {
            "_id": "schedule-monthly-financial",
            "frequency": "monthly",
            "format": "csv",
            "recipients": ["admin@tourapp.local"],
            "next_run": now + timedelta(days=30),
        }
    ]

    return {
        "generated": generated,
        "scheduled": scheduled,
    }


# ============= AUDIT & COMPLIANCE ENDPOINTS =============

@router.get("/audit/summary")
async def get_audit_summary(
    system_page: int = 1,
    system_per_page: int = 10,
    system_search: str = "",
    system_severity: str = "",
    system_service: str = "",
    system_unread_only: bool = False,
    sessions_page: int = 1,
    sessions_per_page: int = 10,
    session_search: str = "",
    session_user_type: str = "",
    session_device_type: str = "",
    security_page: int = 1,
    security_per_page: int = 10,
    security_search: str = "",
    security_event_type: str = "",
    security_date_from: str = "",
    admin: dict = Depends(get_current_admin),
):
    """Get audit and compliance summary data for admin dashboard."""
    db = await get_database()
    now = datetime.now(timezone.utc)
    activity_cutoff = now - timedelta(days=14)
    bookings = await db.bookings.find(
        {},
        {
            "tourist_id": 1,
            "created_at": 1,
            "updated_at": 1,
            "booking_status.status": 1,
            "cart.area_name": 1,
        },
    ).sort("updated_at", -1).to_list(200)
    quotes = await db.quote_requests.aggregate(
        [
            {"$sort": {"updated_at": -1}},
            {"$limit": 200},
            {
                "$project": {
                    "tourist_name": 1,
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "response_count": {"$size": {"$ifNull": ["$responses", []]}},
                }
            },
        ]
    ).to_list(length=200)
    recent_users = await db.users.find(
        {"$or": [{"last_login": {"$gte": activity_cutoff}}, {"updated_at": {"$gte": activity_cutoff}}, {"created_at": {"$gte": activity_cutoff}}]},
        {"full_name": 1, "email": 1, "user_type": 1, "created_at": 1, "updated_at": 1, "last_login": 1, "is_active": 1},
    ).sort("updated_at", -1).limit(200).to_list(length=200)
    recent_admins = await db.admins.find(
        {"$or": [{"last_login": {"$gte": activity_cutoff}}, {"updated_at": {"$gte": activity_cutoff}}, {"created_at": {"$gte": activity_cutoff}}]},
        {"full_name": 1, "email": 1, "created_at": 1, "updated_at": 1, "last_login": 1},
    ).sort("last_login", -1).limit(120).to_list(length=120)

    tourist_ids = {booking.get("tourist_id") for booking in bookings if booking.get("tourist_id")}
    users_by_id = await _load_users_by_id(db, tourist_ids)

    # Activity logs (derived from recent bookings + quotes + user registrations)
    activity_logs = []

    for booking in bookings[:60]:
        tourist = users_by_id.get(booking.get("tourist_id"), {})
        status_value = booking.get("booking_status", {}).get("status", "pending")
        activity_logs.append(
            {
                "_id": f"booking-{booking.get('_id')}",
                "user_name": tourist.get("full_name", "Tourist User"),
                "actionType": "update" if status_value != "pending" else "create",
                "resource": "booking",
                "description": f"Booking {status_value} for {booking.get('cart', {}).get('area_name', 'destination')}",
                "timestamp": booking.get("updated_at") or booking.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 200,
                "changes": None,
            }
        )

    for quote in quotes[:60]:
        response_count = int(quote.get("response_count", 0) or 0)
        activity_logs.append(
            {
                "_id": f"quote-{quote.get('_id')}",
                "user_name": quote.get("tourist_name") or "Tourist User",
                "actionType": "update" if response_count else "create",
                "resource": "tour",
                "description": f"Quote request {quote.get('status', 'open')} with {response_count} response(s)",
                "timestamp": quote.get("updated_at") or quote.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 200,
                "changes": None,
            }
        )

    for user in recent_users[:40]:
        activity_logs.append(
            {
                "_id": f"user-{user.get('_id')}",
                "user_name": user.get("full_name", "User"),
                "actionType": "create",
                "resource": "user",
                "description": f"User registered as {user.get('user_type', 'tourist')}",
                "timestamp": user.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 201,
                "changes": None,
            }
        )

    activity_logs.sort(key=lambda x: x.get("timestamp") or now, reverse=True)
    activity_logs = activity_logs[:150]

    system_filters = {"category": "system"}
    system_filters.update(
        _build_audit_search_query(
            ["title", "message", "service", "error_code", "details"],
            system_search,
        )
    )
    normalized_system_severity = system_severity.strip().casefold()
    normalized_system_service = system_service.strip().casefold()
    if normalized_system_severity:
        system_filters["severity"] = normalized_system_severity
    if normalized_system_service:
        system_filters["service"] = normalized_system_service
    if system_unread_only:
        system_filters["read"] = False

    paged_system_events, system_pagination = await _paginate_audit_events(
        db.audit_events,
        filters=system_filters,
        page=system_page,
        per_page=system_per_page,
    )

    # Sessions (derived from users/admins with recent activity)
    sessions = []
    for user in recent_users:
        last_activity = _coerce_utc_datetime(user.get("last_login") or user.get("updated_at") or user.get("created_at"))
        if not last_activity:
            continue

        session_status = "active" if (now - last_activity) <= timedelta(hours=8) else "idle"
        sessions.append(
            {
                "_id": f"session-user-{user.get('_id')}",
                "user_name": user.get("full_name", "User"),
                "email": user.get("email", "N/A"),
                "user_type": user.get("user_type", "tourist"),
                "status": session_status,
                "device_type": "desktop",
                "ip_address": "N/A",
                "location": "Unknown",
                "created_at": user.get("created_at") or last_activity,
                "last_activity": last_activity,
            }
        )

    for admin_user in recent_admins:
        last_activity = _coerce_utc_datetime(admin_user.get("last_login") or admin_user.get("updated_at") or admin_user.get("created_at"))
        if not last_activity:
            continue

        session_status = "active" if (now - last_activity) <= timedelta(hours=8) else "idle"
        sessions.append(
            {
                "_id": f"session-admin-{admin_user.get('_id')}",
                "user_name": admin_user.get("full_name", "Admin"),
                "email": admin_user.get("email", "N/A"),
                "user_type": "admin",
                "status": session_status,
                "device_type": "desktop",
                "ip_address": "N/A",
                "location": "Admin Console",
                "created_at": admin_user.get("created_at") or last_activity,
                "last_activity": last_activity,
            }
        )

    sessions.sort(key=lambda x: x.get("last_activity") or now, reverse=True)
    sessions = sessions[:120]

    security_filters = {"category": "security"}
    security_filters.update(
        _build_audit_search_query(
            ["title", "description", "user_name", "ip_address", "location", "remediation"],
            security_search,
        )
    )
    normalized_security_event_type = security_event_type.strip().casefold()
    security_date_floor = _parse_filter_date(security_date_from)
    if normalized_security_event_type:
        security_filters["event_type"] = normalized_security_event_type
    if security_date_floor:
        security_filters["timestamp"] = {"$gte": security_date_floor}

    paged_security_events, security_pagination = await _paginate_audit_events(
        db.audit_events,
        filters=security_filters,
        page=security_page,
        per_page=security_per_page,
    )

    failed_login_attempts = await db.audit_events.count_documents({"category": "security", "event_type": "failed_login"})
    suspicious_activities = await db.audit_events.count_documents({"category": "security", "event_type": {"$in": ["brute_force", "suspicious"]}})
    anomalies_detected = await db.audit_events.count_documents({"category": "security", "severity": "critical"})
    rate_limit_hits = await db.audit_events.count_documents({"category": "security", "event_type": "rate_limit"})

    normalized_session_search = session_search.strip().casefold()
    normalized_session_user_type = session_user_type.strip().casefold()
    normalized_session_device_type = session_device_type.strip().casefold()

    filtered_sessions = []
    for session in sessions:
        haystack = " ".join([
            str(session.get("user_name") or ""),
            str(session.get("email") or ""),
            str(session.get("ip_address") or ""),
            str(session.get("location") or ""),
            str(session.get("device_type") or ""),
        ]).casefold()

        if normalized_session_search and normalized_session_search not in haystack:
            continue
        if normalized_session_user_type and str(session.get("user_type") or "").casefold() != normalized_session_user_type:
            continue
        if normalized_session_device_type and str(session.get("device_type") or "").casefold() != normalized_session_device_type:
            continue
        filtered_sessions.append(session)

    filtered_active_sessions = [session for session in filtered_sessions if session.get("status") == "active"]
    unique_users_online = len({session.get("user_name") or "Unknown" for session in filtered_active_sessions})
    avg_session_duration = 0
    if filtered_active_sessions:
        total_duration = 0
        for session in filtered_active_sessions:
            started_at = _coerce_utc_datetime(session.get("created_at")) or now
            last_activity = _coerce_utc_datetime(session.get("last_activity")) or now
            total_duration += max(0, int((last_activity - started_at).total_seconds() // 60))
        avg_session_duration = round(total_duration / len(filtered_active_sessions))

    paged_sessions, sessions_pagination = _paginate_items(filtered_sessions, sessions_page, sessions_per_page)

    activity_stats = {
        "total": len(activity_logs),
        "creates": sum(1 for a in activity_logs if a.get("actionType") == "create"),
        "updates": sum(1 for a in activity_logs if a.get("actionType") == "update"),
        "deletes": sum(1 for a in activity_logs if a.get("actionType") == "delete"),
    }

    user_activity_counter = defaultdict(int)
    for log in activity_logs:
        user_activity_counter[log.get("user_name", "Unknown")] += 1

    top_users = [
        {"name": name, "count": count}
        for name, count in sorted(user_activity_counter.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    security_score = max(
        0,
        min(
            100,
            100
            - min(30, suspicious_activities)
            - min(30, anomalies_detected)
            - min(20, failed_login_attempts)
            - min(20, rate_limit_hits),
        ),
    )

    return {
        "activityLogs": activity_logs,
        "systemEvents": paged_system_events,
        "systemEventsPagination": system_pagination,
        "sessions": paged_sessions,
        "sessionsPagination": sessions_pagination,
        "sessionsSummary": {
            "activeCount": len(filtered_active_sessions),
            "uniqueUsersOnline": unique_users_online,
            "avgSessionDuration": avg_session_duration,
        },
        "securityEvents": paged_security_events,
        "securityEventsPagination": security_pagination,
        "failedLoginAttempts": failed_login_attempts,
        "suspiciousActivities": suspicious_activities,
        "anomaliesDetected": anomalies_detected,
        "rateLimitHits": rate_limit_hits,
        "activityStats": activity_stats,
        "topUsers": top_users,
        "securityScore": security_score,
    }


@router.get("/audit/authorization-decisions")
async def get_authorization_decision_report(
    hours: int = 24,
    limit: int = 200,
    principal_type: str = "",
    decision: str = "",
    permission: str = "",
    path_contains: str = "",
    admin: dict = Depends(get_current_admin),
):
    """Get authorization decision observability metrics and recent events."""
    db = await get_database()
    _ = admin
    return await build_authorization_decision_report(
        db,
        hours=hours,
        limit=limit,
        principal_type=principal_type,
        decision=decision,
        permission=permission,
        path_contains=path_contains,
    )


# ============= REPORTS & ANALYTICS ENDPOINTS =============

@router.get("/reports/summary")
async def get_reports_summary(admin: dict = Depends(get_current_admin)):
    """Get reports listing, schedules, and dashboard metadata for admin reports UI."""
    db = await get_database()
    now = datetime.now(timezone.utc)

    total_quotes = await db.quote_requests.count_documents({})
    total_bookings = await db.bookings.count_documents({})
    total_operators = await db.operator_profiles.count_documents({})
    total_tourists = await db.users.count_documents({"user_type": "tourist"})

    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    completed_bookings = await db.bookings.count_documents({"booking_status.status": "completed"})

    persisted_reports = await db.admin_reports.find(
        {},
        {
            "name": 1,
            "type": 1,
            "status": 1,
            "size": 1,
            "generated_by": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    ).sort("updated_at", -1).to_list(200)
    for item in persisted_reports:
        item["_id"] = str(item["_id"])

    persisted_schedules = await db.admin_report_schedules.find(
        {},
        {
            "report_name": 1,
            "frequency": 1,
            "recipients": 1,
            "format": 1,
            "status": 1,
            "next_run": 1,
            "runs_count": 1,
            "created_at": 1,
        },
    ).sort("created_at", -1).to_list(200)
    for item in persisted_schedules:
        item["_id"] = str(item["_id"])

    persisted_dashboards = await db.admin_dashboards.find(
        {},
        {
            "name": 1,
            "description": 1,
            "widgets": 1,
            "created_at": 1,
            "shared_with": 1,
        },
    ).sort("created_at", -1).to_list(100)
    for item in persisted_dashboards:
        serialized = _serialize_dashboard(item)
        item.clear()
        item.update(serialized)

    report_items = _default_admin_report_items(now=now, admin=admin)

    scheduled_items = [
        {
            "_id": "schedule-monthly-revenue",
            "report_name": "Monthly Revenue Report",
            "frequency": "Monthly",
            "recipients": ["admin@tourapp.local"],
            "format": "PDF",
            "status": "active",
            "next_run": now + timedelta(days=30),
            "runs_count": max(1, now.month - 1),
        },
        {
            "_id": "schedule-weekly-performance",
            "report_name": "Weekly Performance Summary",
            "frequency": "Weekly",
            "recipients": ["ops@tourapp.local"],
            "format": "Excel",
            "status": "active",
            "next_run": now + timedelta(days=7),
            "runs_count": 8,
        },
    ]

    dashboard_items = [
        {
            "_id": "dashboard-executive",
            "name": "Executive Dashboard",
            "description": "Executive summary across revenue, bookings, and top operator performance.",
            "widgets": [
                {"key": "revenue", "name": "Revenue Chart"},
                {"key": "bookings", "name": "Bookings Graph"},
                {"key": "operators", "name": "Top Operators"},
                {"key": "metrics", "name": "Key Metrics"},
            ],
            "created_at": now - timedelta(days=14),
            "shared_with": ["leadership@tourapp.local"],
        },
        {
            "_id": "dashboard-operations",
            "name": "Operations Dashboard",
            "description": "Operations-focused dashboard for booking health, quote throughput, and response times.",
            "widgets": [
                {"key": "bookings", "name": "Bookings Graph"},
                {"key": "operators", "name": "Top Operators"},
                {"key": "metrics", "name": "Key Metrics"},
            ],
            "created_at": now - timedelta(days=10),
            "shared_with": ["ops@tourapp.local"],
        },
    ]

    prebuilt_templates = [
        {"id": 1, "name": "Revenue Analysis", "icon": "💰"},
        {"id": 2, "name": "Operator Performance", "icon": "🚀"},
        {"id": 3, "name": "Booking Trends", "icon": "📈"},
        {"id": 4, "name": "Customer Satisfaction", "icon": "⭐"},
        {"id": 5, "name": "Payment Summary", "icon": "💳"},
        {"id": 6, "name": "Quarterly Report", "icon": "📊"},
        {"id": 7, "name": "Year-end Review", "icon": "🏆"},
        {"id": 8, "name": "Commission Report", "icon": "🎯"},
    ]

    metrics = {
        "total_quotes": total_quotes,
        "closed_quotes": closed_quotes,
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "total_operators": total_operators,
        "total_tourists": total_tourists,
    }

    return {
        "reports": persisted_reports if persisted_reports else report_items,
        "scheduledReports": persisted_schedules if persisted_schedules else scheduled_items,
        "dashboards": persisted_dashboards if persisted_dashboards else dashboard_items,
        "prebuiltTemplates": prebuilt_templates,
        "metrics": metrics,
    }


@router.get("/reports/{report_id}")
async def get_admin_report_details(report_id: str, admin: dict = Depends(get_current_admin)):
    """Return live detail payload for a single report card."""
    db = await get_database()
    report = await _find_admin_report(db, report_id, admin)
    return await _build_admin_report_payload(db, report)


@router.get("/reports/{report_id}/download")
async def download_admin_report(report_id: str, format: str = "json", admin: dict = Depends(get_current_admin)):
    """Download a generated report payload as JSON, CSV, or PDF."""
    db = await get_database()
    report = await _find_admin_report(db, report_id, admin)
    payload = await _build_admin_report_payload(db, report)

    normalized_format = format.lower()
    filename_base = _slugify_filename(report.get("name", "report"))

    if normalized_format == "csv":
        content = _report_payload_to_csv(payload)
        media_type = "text/csv"
        filename = f"{filename_base}.csv"
    elif normalized_format == "pdf":
        content = _render_text_pdf(_report_payload_to_text_lines(payload))
        media_type = "application/pdf"
        filename = f"{filename_base}.pdf"
    elif normalized_format == "json":
        content = json.dumps(payload, default=str, indent=2)
        media_type = "application/json"
        filename = f"{filename_base}.json"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported report format")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/dashboards/{dashboard_id}")
async def get_admin_dashboard(dashboard_id: str, admin: dict = Depends(get_current_admin)):
    """Return a single dashboard document for the reports UI."""
    db = await get_database()
    dashboard = await db.admin_dashboards.find_one(_dashboard_query(dashboard_id))
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return {"dashboard": _serialize_dashboard(dashboard)}


@router.post("/reports/dashboards")
async def create_admin_dashboard(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a persisted admin dashboard."""
    db = await get_database()

    name = str((payload or {}).get("name") or "").strip()
    widgets = _normalize_dashboard_widgets((payload or {}).get("widgets") or [])
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dashboard name is required")
    if not widgets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select at least one widget")

    document = {
        "name": name,
        "description": str((payload or {}).get("description") or "").strip(),
        "widgets": widgets,
        "shared_with": [str(entry).strip() for entry in ((payload or {}).get("shared_with") or []) if str(entry).strip()],
        "created_by": admin.get("_id"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await db.admin_dashboards.insert_one(document)
    document["_id"] = result.inserted_id
    return {"message": "Dashboard created", "dashboard": _serialize_dashboard(document)}


@router.patch("/reports/dashboards/{dashboard_id}")
async def update_admin_dashboard(dashboard_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    """Update dashboard metadata, widgets, or sharing."""
    db = await get_database()
    query = _dashboard_query(dashboard_id)

    update_data = {"updated_at": datetime.now(timezone.utc), "updated_by": admin.get("_id")}
    if "name" in (payload or {}):
        name = str((payload or {}).get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dashboard name is required")
        update_data["name"] = name
    if "description" in (payload or {}):
        update_data["description"] = str((payload or {}).get("description") or "").strip()
    if "widgets" in (payload or {}):
        widgets = _normalize_dashboard_widgets((payload or {}).get("widgets") or [])
        if not widgets:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select at least one widget")
        update_data["widgets"] = widgets
    if "shared_with" in (payload or {}):
        update_data["shared_with"] = [str(entry).strip() for entry in ((payload or {}).get("shared_with") or []) if str(entry).strip()]

    result = await db.admin_dashboards.update_one(query, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    dashboard = await db.admin_dashboards.find_one(query)
    return {"message": "Dashboard updated", "dashboard": _serialize_dashboard(dashboard)}


@router.delete("/reports/dashboards/{dashboard_id}")
async def delete_admin_dashboard(dashboard_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a persisted admin dashboard."""
    db = await get_database()
    result = await db.admin_dashboards.delete_one(_dashboard_query(dashboard_id))
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return {"message": "Dashboard deleted"}


# ============= SETTINGS & SYSTEM HEALTH ENDPOINTS =============

@router.get("/settings/summary")
async def get_settings_summary(admin: dict = Depends(get_current_admin)):
    """Get settings and health summary for admin settings UI."""
    db = await get_database()
    now = datetime.now(timezone.utc)

    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    operators = await db.users.count_documents({"user_type": "operator"})
    tourists = await db.users.count_documents({"user_type": "tourist"})
    total_bookings = await db.bookings.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})

    admins = await db.admins.find({}).sort("last_login", -1).to_list(None)
    role_to_display = {
        "super_admin": "admin",
        "admin": "admin",
        "moderator": "manager",
    }

    admin_users = [
        {
            "_id": str(a.get("_id")),
            "name": a.get("full_name", "Admin User"),
            "email": a.get("email", "N/A"),
            "role": role_to_display.get(a.get("role", "admin"), "manager"),
            "status": "active" if a.get("is_active", True) else "inactive",
            "lastLogin": a.get("last_login") or a.get("updated_at") or a.get("created_at") or now,
        }
        for a in admins
    ]

    if not admin_users:
        admin_users = [
            {
                "_id": "admin-default",
                "name": admin.get("full_name", "Admin User"),
                "email": admin.get("email", "admin@tourapp.local"),
                "role": admin.get("role", "admin"),
                "status": "active",
                "lastLogin": now,
            }
        ]

    settings_data = {
        "general": {
            "appName": "Tour App",
            "appUrl": "http://localhost:5173",
            "supportEmail": "support@tourapp.com",
            "supportPhone": "+91-9876543210",
            "defaultLanguage": "en",
            "timezone": "IST",
            "dateFormat": "DD/MM/YYYY",
            "enableNotifications": True,
            "enableReports": True,
            "enableAnalytics": True,
            "enableApiAccess": True,
            "maintenanceMode": False,
        }
    }

    persisted_general = await db.admin_settings.find_one({"key": "general"})
    if persisted_general and isinstance(persisted_general.get("value"), dict):
        settings_data["general"] = {
            **settings_data["general"],
            **persisted_general["value"],
        }

    system_health = {
        "overall": "healthy",
        "database": "healthy",
        "apiServer": "healthy",
        "cache": "healthy",
        "emailService": "healthy",
        "storage": "healthy",
        "dbResponseTime": max(20, min(120, 35 + open_quotes)),
        "dbQueries": max(100, total_bookings + open_quotes + total_users),
        "apiUptime": "Active",
        "cpuUsage": min(85, 20 + (operators % 50)),
        "memoryUsage": min(90, 30 + (total_users % 60)),
        "cacheHitRate": max(70, 95 - (open_quotes % 20)),
        "cachedItems": max(100, total_users * 12),
        "cacheSize": max(64, (total_users // 5) + 128),
        "emailsSent": max(0, total_bookings + open_quotes),
        "emailsFailed": 0,
        "emailQueueSize": max(0, open_quotes // 3),
        "storageUsed": max(5, (total_users // 10) + (total_bookings // 20) + 40),
        "storageTotal": 500,
        "storagePercent": min(99, max(1, int((max(5, (total_users // 10) + (total_bookings // 20) + 40) / 500) * 100))),
    }

    backup_info = {
        "lastBackup": now - timedelta(hours=8),
        "lastBackupSize": "2.4 GB",
        "totalFiles": max(1000, total_users * 200),
        "filesSize": f"{max(10, total_users // 3)} GB",
        "filesLastBackup": now - timedelta(hours=7),
    }

    backup_history = [
        {"_id": "bkp-1", "date": now - timedelta(days=1), "size": "2.4 GB", "status": "completed"},
        {"_id": "bkp-2", "date": now - timedelta(days=2), "size": "2.3 GB", "status": "completed"},
        {"_id": "bkp-3", "date": now - timedelta(days=3), "size": "2.5 GB", "status": "completed"},
    ]

    maintenance_info = {
        "cacheSize": f"{system_health['cacheSize']} MB",
        "tempFiles": max(20, total_users // 2),
        "logsSize": "2.1 GB",
        "lastOptimized": now - timedelta(days=7),
        "fragmentation": 8,
    }

    security_settings = {
        "sessionTimeout": 30,
        "maxLoginAttempts": 5,
        "lockoutDuration": 15,
        "twoFactorEnabled": True,
        "enforceStrongPasswords": True,
        "passwordMinLength": 8,
        "passwordExpiry": 90,
        "requireUppercase": True,
        "requireNumbers": True,
        "requireSpecialChars": True,
        "ipWhitelist": ["192.168.1.1", "10.0.0.1", "172.16.0.1"],
        "enableEncryption": True,
        "enableSSL": True,
        "enableAuditLog": True,
        "enableDataMasking": True,
    }

    persisted_security = await db.admin_settings.find_one({"key": "security"})
    if persisted_security and isinstance(persisted_security.get("value"), dict):
        security_settings = {
            **security_settings,
            **persisted_security["value"],
        }

    api_keys = [
        {
            "_id": "key-mobile-app",
            "name": "Mobile App",
            "key": "sk_live_abc123def456ghi789",
            "created_at": now - timedelta(days=120),
            "lastUsed": now - timedelta(hours=1),
        },
        {
            "_id": "key-web-dashboard",
            "name": "Web Dashboard",
            "key": "sk_live_xyz789uvw456rst123",
            "created_at": now - timedelta(days=180),
            "lastUsed": now - timedelta(hours=3),
        },
    ]

    webhooks = [
        {"_id": "wh-booking", "event": "booking.created", "url": "https://example.com/booking-created", "status": "active"},
        {"_id": "wh-payment", "event": "payment.completed", "url": "https://example.com/payment-webhook", "status": "active"},
    ]

    third_party_services = [
        {"_id": "svc-stripe", "name": "Stripe (Payments)", "status": "connected"},
        {"_id": "svc-twilio", "name": "Twilio (SMS)", "status": "connected"},
        {"_id": "svc-sendgrid", "name": "SendGrid (Email)", "status": "connected"},
        {"_id": "svc-analytics", "name": "Google Analytics", "status": "disconnected"},
    ]

    integration_settings = {
        "rateLimitPerMinute": 100,
        "rateLimitPerHour": 5000,
        "rateLimitPerDay": 100000,
    }

    persisted_integration = await db.admin_settings.find_one({"key": "integration"})
    if persisted_integration and isinstance(persisted_integration.get("value"), dict):
        integration_settings = {
            **integration_settings,
            **persisted_integration["value"],
        }

    persisted_keys = await db.admin_api_keys.find({}).sort("created_at", -1).to_list(200)
    if persisted_keys:
        api_keys = persisted_keys
        for key in api_keys:
            key["_id"] = str(key["_id"])

    persisted_webhooks = await db.admin_webhooks.find({}).sort("created_at", -1).to_list(200)
    if persisted_webhooks:
        webhooks = persisted_webhooks
        for webhook in webhooks:
            webhook["_id"] = str(webhook["_id"])

    metrics = {
        "totalUsers": total_users,
        "activeUsers": active_users,
        "operators": operators,
        "tourists": tourists,
        "openQuotes": open_quotes,
        "totalBookings": total_bookings,
    }

    return {
        "settings": settings_data,
        "systemHealth": system_health,
        "adminUsers": admin_users,
        "backupInfo": backup_info,
        "backupHistory": backup_history,
        "maintenanceInfo": maintenance_info,
        "securitySettings": security_settings,
        "apiKeys": api_keys,
        "webhooks": webhooks,
        "thirdPartyServices": third_party_services,
        "integrationSettings": integration_settings,
        "metrics": metrics,
    }


@router.post("/reports")
async def create_admin_report(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a new admin report record."""
    db = await get_database()

    name = (payload or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report name is required")

    report_type = (payload or {}).get("type", "revenue")
    report_status = (payload or {}).get("status", "draft")
    size = (payload or {}).get("size", "0 MB")

    document = {
        "name": name,
        "type": report_type,
        "status": report_status,
        "size": size,
        "generated_by": admin.get("full_name", "Admin User"),
        "description": (payload or {}).get("description"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await db.admin_reports.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "Report created", "report": document}


@router.delete("/reports/{report_id}")
async def delete_admin_report(report_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an admin report record."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(report_id)}
    except Exception:
        query = {"_id": report_id}

    result = await db.admin_reports.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {"message": "Report deleted"}


@router.post("/reports/schedules")
async def create_report_schedule(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a scheduled report entry."""
    db = await get_database()

    report_name = (payload or {}).get("report_name", "").strip() or "Scheduled Report"
    recipients = (payload or {}).get("recipients") or []
    if not isinstance(recipients, list) or not recipients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one recipient is required")

    frequency = ((payload or {}).get("frequency") or "monthly").lower()
    if frequency == "daily":
        next_run = datetime.now(timezone.utc) + timedelta(days=1)
    elif frequency == "weekly":
        next_run = datetime.now(timezone.utc) + timedelta(days=7)
    else:
        next_run = datetime.now(timezone.utc) + timedelta(days=30)

    schedule = {
        "report_name": report_name,
        "report_id": (payload or {}).get("report_id"),
        "frequency": frequency.capitalize(),
        "recipients": recipients,
        "format": ((payload or {}).get("format") or "pdf").upper(),
        "status": "active",
        "next_run": next_run,
        "runs_count": 0,
        "created_by": admin.get("_id"),
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.admin_report_schedules.insert_one(schedule)
    schedule["_id"] = str(result.inserted_id)
    return {"message": "Report schedule created", "schedule": schedule}


@router.patch("/reports/schedules/{schedule_id}")
async def update_report_schedule(schedule_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    """Update report schedule status or fields."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(schedule_id)}
    except Exception:
        query = {"_id": schedule_id}

    update_data = {}
    if "status" in (payload or {}):
        update_data["status"] = (payload or {}).get("status")
    if "frequency" in (payload or {}):
        update_data["frequency"] = str((payload or {}).get("frequency", "Monthly")).capitalize()
    if "format" in (payload or {}):
        update_data["format"] = str((payload or {}).get("format", "PDF")).upper()

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    result = await db.admin_report_schedules.update_one(query, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    return {"message": "Schedule updated"}


@router.delete("/reports/schedules/{schedule_id}")
async def delete_report_schedule(schedule_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a scheduled report entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(schedule_id)}
    except Exception:
        query = {"_id": schedule_id}

    result = await db.admin_report_schedules.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    return {"message": "Schedule deleted"}


@router.post("/settings/general")
async def save_general_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist general settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "general"},
        {
            "$set": {
                "key": "general",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "General settings saved"}


@router.post("/settings/security")
async def save_security_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist security settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "security"},
        {
            "$set": {
                "key": "security",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "Security settings saved"}


@router.post("/settings/integration")
async def save_integration_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist integration settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "integration"},
        {
            "$set": {
                "key": "integration",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "Integration settings saved"}


@router.post("/settings/api-keys")
async def create_api_key(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create and store a new admin API key entry."""
    db = await get_database()
    name = (payload or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key name is required")

    document = {
        "name": name,
        "key": f"sk_live_{uuid4().hex[:24]}",
        "permissions": (payload or {}).get("permissions") or [],
        "created_at": datetime.now(timezone.utc),
        "lastUsed": None,
        "created_by": admin.get("_id"),
    }
    result = await db.admin_api_keys.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "API key created", "apiKey": document}


@router.delete("/settings/api-keys/{key_id}")
async def delete_api_key(key_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an admin API key entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(key_id)}
    except Exception:
        query = {"_id": key_id}

    result = await db.admin_api_keys.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked"}


@router.post("/settings/webhooks")
async def create_webhook(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a webhook configuration entry."""
    db = await get_database()
    event = (payload or {}).get("event", "").strip()
    url = (payload or {}).get("url", "").strip()
    if not event or not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook event and URL are required")

    document = {
        "event": event,
        "url": url,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "created_by": admin.get("_id"),
    }
    result = await db.admin_webhooks.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "Webhook created", "webhook": document}


@router.delete("/settings/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a webhook configuration entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(webhook_id)}
    except Exception:
        query = {"_id": webhook_id}

    result = await db.admin_webhooks.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return {"message": "Webhook deleted"}


@router.patch("/settings/admin-users/{admin_id}")
async def update_admin_user_entry(admin_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    """Update admin user entry fields used by admin settings UI."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(admin_id)}
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin ID")

    update_data = {}
    if "status" in (payload or {}):
        update_data["is_active"] = (payload or {}).get("status") == "active"

    if "role" in (payload or {}):
        requested_role = str((payload or {}).get("role", "manager")).lower()
        mapped_role = {
            "admin": "admin",
            "manager": "moderator",
            "supervisor": "moderator",
            "super_admin": "super_admin",
            "moderator": "moderator",
        }.get(requested_role, "moderator")
        update_data["role"] = mapped_role

    if "name" in (payload or {}):
        update_data["full_name"] = (payload or {}).get("name")

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await db.admins.update_one(query, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    return {"message": "Admin user updated"}
