from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_database
from ..models.ticket import TicketCommentCreate, TicketCreate, TicketStatusUpdate
from ..routers.admin import get_current_admin, get_current_admin_access_context
from ..routers.auth import get_current_operator_access_context
from ..utils.email import send_support_ticket_status_email


router = APIRouter(tags=["Support Tickets"])

AUTO_REPLY_STATUSES = {"acknowledged", "in_progress", "completed"}


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


def _serialize_history_item(item: dict) -> dict:
    return {
        "status": item.get("status"),
        "message": item.get("message"),
        "public_reply": item.get("public_reply"),
        "actor_type": item.get("actor_type"),
        "actor_name": item.get("actor_name"),
        "created_at": _serialize_datetime(item.get("created_at")),
    }


def _serialize_comment(item: dict) -> dict:
    return {
        "message": item.get("message"),
        "attachments": item.get("attachments", []),
        "actor_type": item.get("actor_type"),
        "actor_name": item.get("actor_name"),
        "created_at": _serialize_datetime(item.get("created_at")),
    }


def _serialize_ticket(document: dict) -> dict:
    return {
        "_id": str(document.get("_id")),
        "title": document.get("title"),
        "description": document.get("description"),
        "category": document.get("category"),
        "priority": document.get("priority"),
        "status": document.get("status"),
        "requester_user_id": document.get("requester_user_id"),
        "requester_name": document.get("requester_name"),
        "requester_email": document.get("requester_email"),
        "operator_profile_id": document.get("operator_profile_id"),
        "operator_business_name": document.get("operator_business_name"),
        "organization_id": document.get("organization_id"),
        "assignee_admin_id": document.get("assignee_admin_id"),
        "assignee_admin_name": document.get("assignee_admin_name"),
        "latest_public_reply": document.get("latest_public_reply"),
        "attachments": document.get("attachments", []),
        "created_at": _serialize_datetime(document.get("created_at")),
        "updated_at": _serialize_datetime(document.get("updated_at")),
        "status_history": [_serialize_history_item(item) for item in document.get("status_history", [])],
        "comments": [_serialize_comment(item) for item in document.get("comments", [])],
    }


def _encode_ticket_cursor(*, created_at: datetime, ticket_id: ObjectId) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {
        "created_at": created_at.isoformat(),
        "ticket_id": str(ticket_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _decode_ticket_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        created_at = datetime.fromisoformat(payload["created_at"])
        ticket_id = ObjectId(payload["ticket_id"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at, ticket_id


async def _get_admin_display_name(db, *, admin_id: str | None) -> str | None:
    if not admin_id or not ObjectId.is_valid(admin_id):
        return None
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        return None
    return admin.get("full_name") or admin.get("email")


async def _create_in_app_ticket_reply(
    db,
    *,
    user_id: str,
    subject: str,
    message: str,
    ticket_id: str,
    status_value: str,
    now: datetime,
):
    campaign = {
        "type": "alert",
        "status": "sent",
        "recipient_type": "direct",
        "recipient_filter": {},
        "channels": ["in_app"],
        "subject": subject,
        "message": message,
        "delivery_stats": {
            "accepted": 1,
            "delivered": 1,
            "opened": 0,
            "clicked": 0,
            "failed": 0,
            "suppressed": 0,
            "read": 0,
        },
        "created_at": now,
        "updated_at": now,
        "scheduled_for": now,
        "sent_at": now,
    }
    campaign_result = await db.notification_campaigns.insert_one(campaign)
    await db.notification_deliveries.insert_one(
        {
            "campaign_id": str(campaign_result.inserted_id),
            "user_id": user_id,
            "subject": subject,
            "message": message,
            "type": "alert",
            "channel": "in_app",
            "status": "delivered",
            "created_at": now,
            "delivered_at": now,
            "read_at": None,
            "metadata": {
                "ticket_id": ticket_id,
                "status": status_value,
            },
        }
    )


def _normalize_attachments(items: list[str] | None) -> list[str]:
    return [item.strip() for item in (items or []) if isinstance(item, str) and item.strip()]


def _build_comment(*, actor_type: str, actor_name: str | None, message: str | None, attachments: list[str], now: datetime) -> dict:
    return {
        "message": message.strip() if isinstance(message, str) and message.strip() else None,
        "attachments": _normalize_attachments(attachments),
        "actor_type": actor_type,
        "actor_name": actor_name,
        "created_at": now,
    }


def _ensure_comment_payload(payload: TicketCommentCreate) -> tuple[str | None, list[str]]:
    attachments = _normalize_attachments(payload.attachments)
    message = payload.message.strip() if payload.message and payload.message.strip() else None
    if not message and not attachments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment message or attachments are required")
    return message, attachments


def _status_message(status_value: str, title: str, public_reply: str | None) -> tuple[str, str]:
    human_status = status_value.replace("_", " ").title()
    subject = f"Support ticket {human_status}: {title}"
    body = {
        "acknowledged": "Your support request has been acknowledged by our admin team.",
        "in_progress": "Your support request is currently being worked on.",
        "completed": "Your support request has been completed.",
    }.get(status_value, f"Your support ticket is now {human_status.lower()}.")
    if public_reply:
        body = f"{body} Reply: {public_reply}"
    return subject, body


@router.get("/operator/tickets")
async def list_operator_tickets(
    status_value: str | None = None,
    cursor: str | None = None,
    page_size: int = Query(10, ge=1, le=100),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    base_query = {"organization_id": access_context["organization"]["_id"]}
    if status_value:
        base_query["status"] = status_value

    cursor_match = None
    if cursor:
        cursor_created_at, cursor_ticket_id = _decode_ticket_cursor(cursor)
        cursor_match = {
            "$or": [
                {"created_at": {"$lt": cursor_created_at}},
                {"created_at": cursor_created_at, "_id": {"$lt": cursor_ticket_id}},
            ]
        }

    total_count = await db.support_tickets.count_documents({"organization_id": access_context["organization"]["_id"]})
    open_count = await db.support_tickets.count_documents({"organization_id": access_context["organization"]["_id"], "status": "open"})
    filtered_total = await db.support_tickets.count_documents(base_query)

    effective_query = dict(base_query)
    if cursor_match:
        effective_query["$and"] = [cursor_match]

    tickets = await db.support_tickets.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(tickets) > page_size
    tickets = tickets[:page_size]

    next_cursor = None
    if has_more and tickets:
        last_ticket = tickets[-1]
        next_cursor = _encode_ticket_cursor(created_at=last_ticket["created_at"], ticket_id=last_ticket["_id"])

    total_pages = max(1, (filtered_total + page_size - 1) // page_size)
    return {
        "tickets": [_serialize_ticket(ticket) for ticket in tickets],
        "pagination": {
            "page_size": page_size,
            "total_items": filtered_total,
            "total_pages": total_pages,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
        "summary": {
            "total": total_count,
            "open": open_count,
        },
    }


@router.post("/operator/tickets", status_code=status.HTTP_201_CREATED)
async def create_operator_ticket(
    payload: TicketCreate,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    now = _utcnow()
    ticket = {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "category": payload.category.strip().lower(),
        "priority": payload.priority,
        "attachments": _normalize_attachments(payload.attachments),
        "status": "open",
        "organization_id": access_context["organization"]["_id"],
        "operator_profile_id": access_context["operator_profile"]["_id"],
        "operator_business_name": access_context["operator_profile"].get("business_name"),
        "requester_user_id": access_context["principal"]["_id"],
        "requester_name": access_context["principal"].get("full_name"),
        "requester_email": access_context["principal"].get("email"),
        "assignee_admin_id": None,
        "assignee_admin_name": None,
        "latest_public_reply": None,
        "comments": [],
        "status_history": [
            {
                "status": "open",
                "message": "Ticket created",
                "public_reply": None,
                "actor_type": "operator",
                "actor_name": access_context["principal"].get("full_name") or access_context["principal"].get("email"),
                "created_at": now,
            }
        ],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.support_tickets.insert_one(ticket)
    ticket["_id"] = result.inserted_id
    return {"message": "Support ticket created", "ticket": _serialize_ticket(ticket)}


@router.get("/operator/tickets/{ticket_id}")
async def get_operator_ticket(ticket_id: str, access_context: dict = Depends(get_current_operator_access_context)):
    db = await get_database()
    try:
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id), "organization_id": access_context["organization"]["_id"]})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID") from exc
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return {"ticket": _serialize_ticket(ticket)}


@router.post("/operator/tickets/{ticket_id}/comments")
async def add_operator_ticket_comment(
    ticket_id: str,
    payload: TicketCommentCreate,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    try:
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id), "organization_id": access_context["organization"]["_id"]})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID") from exc
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    message, attachments = _ensure_comment_payload(payload)
    now = _utcnow()
    comment = _build_comment(
        actor_type="operator",
        actor_name=access_context["principal"].get("full_name") or access_context["principal"].get("email"),
        message=message,
        attachments=attachments,
        now=now,
    )
    comments = list(ticket.get("comments", []))
    comments.append(comment)
    await db.support_tickets.update_one({"_id": ticket["_id"]}, {"$set": {"comments": comments, "updated_at": now}})
    ticket["comments"] = comments
    ticket["updated_at"] = now
    return {"message": "Comment added", "ticket": _serialize_ticket(ticket)}


@router.get("/admin/tickets")
async def list_admin_tickets(
    status_value: str | None = None,
    priority: str | None = None,
    ticket_id: str | None = None,
    cursor: str | None = None,
    page_size: int = Query(10, ge=1, le=100),
    admin_context: dict = Depends(get_current_admin_access_context),
):
    db = await get_database()
    query = {}
    if status_value:
        query["status"] = status_value
    if priority:
        query["priority"] = priority
    total_count = await db.support_tickets.count_documents({})
    open_count = await db.support_tickets.count_documents({"status": "open"})
    filtered_total = 0

    cursor_match = None
    if cursor:
        cursor_created_at, cursor_ticket_id = _decode_ticket_cursor(cursor)
        cursor_match = {
            "$or": [
                {"created_at": {"$lt": cursor_created_at}},
                {"created_at": cursor_created_at, "_id": {"$lt": cursor_ticket_id}},
            ]
        }

    if ticket_id and ticket_id.strip():
        escaped_ticket_id = re.escape(ticket_id.strip())
        match_conditions = dict(query)
        pipeline = [
            {"$addFields": {"_id_string": {"$toString": "$_id"}}},
            {"$match": {**match_conditions, "_id_string": {"$regex": escaped_ticket_id, "$options": "i"}}},
        ]

        if cursor_match:
            pipeline.append({"$match": cursor_match})

        count_pipeline = pipeline[:2] + [{"$count": "count"}]
        count_result = await db.support_tickets.aggregate(count_pipeline).to_list(length=1)
        filtered_total = count_result[0]["count"] if count_result else 0

        tickets = await db.support_tickets.aggregate(
            pipeline
            + [
                {"$sort": {"created_at": -1, "_id": -1}},
                {"$limit": page_size + 1},
            ]
        ).to_list(length=page_size + 1)
    else:
        filtered_total = await db.support_tickets.count_documents(query)
        effective_query = dict(query)
        if cursor_match:
            effective_query["$and"] = [cursor_match]
        tickets = await db.support_tickets.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)

    has_more = len(tickets) > page_size
    tickets = tickets[:page_size]
    next_cursor = None
    if has_more and tickets:
        last_ticket = tickets[-1]
        next_cursor = _encode_ticket_cursor(created_at=last_ticket["created_at"], ticket_id=last_ticket["_id"])

    total_pages = max(1, (filtered_total + page_size - 1) // page_size)
    return {
        "tickets": [_serialize_ticket(ticket) for ticket in tickets],
        "pagination": {
            "page_size": page_size,
            "total_items": filtered_total,
            "total_pages": total_pages,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
        "summary": {
            "total": total_count,
            "open": open_count,
        },
    }


@router.get("/admin/tickets/{ticket_id}")
async def get_admin_ticket(ticket_id: str, admin_context: dict = Depends(get_current_admin_access_context)):
    db = await get_database()
    try:
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID") from exc
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return {"ticket": _serialize_ticket(ticket)}


@router.post("/admin/tickets/{ticket_id}/comments")
async def add_admin_ticket_comment(
    ticket_id: str,
    payload: TicketCommentCreate,
    admin_context: dict = Depends(get_current_admin_access_context),
    current_admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    try:
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID") from exc
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    message, attachments = _ensure_comment_payload(payload)
    now = _utcnow()
    comment = _build_comment(
        actor_type="admin",
        actor_name=current_admin.get("full_name") or current_admin.get("email"),
        message=message,
        attachments=attachments,
        now=now,
    )
    comments = list(ticket.get("comments", []))
    comments.append(comment)
    await db.support_tickets.update_one({"_id": ticket["_id"]}, {"$set": {"comments": comments, "updated_at": now}})
    ticket["comments"] = comments
    ticket["updated_at"] = now
    return {"message": "Comment added", "ticket": _serialize_ticket(ticket)}


@router.patch("/admin/tickets/{ticket_id}")
async def update_admin_ticket(
    ticket_id: str,
    payload: TicketStatusUpdate,
    admin_context: dict = Depends(get_current_admin_access_context),
    current_admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    try:
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID") from exc
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    now = _utcnow()
    previous_status = ticket.get("status")
    assignee_admin_id = payload.assignee_admin_id or str(current_admin.get("_id"))
    assignee_admin_name = await _get_admin_display_name(db, admin_id=assignee_admin_id)
    public_reply = payload.public_reply.strip() if payload.public_reply else None

    history = list(ticket.get("status_history", []))
    history.append(
        {
            "status": payload.status,
            "message": f"Ticket moved to {payload.status.replace('_', ' ')}",
            "public_reply": public_reply,
            "actor_type": "admin",
            "actor_name": current_admin.get("full_name") or current_admin.get("email"),
            "created_at": now,
        }
    )

    update_data = {
        "status": payload.status,
        "assignee_admin_id": assignee_admin_id,
        "assignee_admin_name": assignee_admin_name,
        "latest_public_reply": public_reply,
        "status_history": history,
        "updated_at": now,
    }
    await db.support_tickets.update_one({"_id": ticket["_id"]}, {"$set": update_data})
    ticket.update(update_data)

    if ticket.get("requester_user_id") and payload.status in AUTO_REPLY_STATUSES and payload.status != previous_status:
        subject, message = _status_message(payload.status, ticket.get("title", "Support ticket"), public_reply)
        await _create_in_app_ticket_reply(
            db,
            user_id=ticket["requester_user_id"],
            subject=subject,
            message=message,
            ticket_id=str(ticket["_id"]),
            status_value=payload.status,
            now=now,
        )
        send_support_ticket_status_email(
            ticket.get("requester_email"),
            ticket_id=str(ticket["_id"]),
            ticket_title=ticket.get("title", "Support ticket"),
            status_value=payload.status,
            full_name=ticket.get("requester_name"),
            public_reply=public_reply,
        )

    return {"message": "Ticket updated", "ticket": _serialize_ticket(ticket)}