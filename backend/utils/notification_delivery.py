from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from ..config import settings
from .notifications import (
    _serialize_datetime,
    _to_object_id,
    _utcnow,
    append_admin_alert,
    append_delivery_attempt,
    get_user_preferences_document,
    list_matching_notification_recipients,
    record_worker_run,
    refresh_campaign_delivery_stats,
)


class InAppNotificationAdapter:
    channel = "in_app"
    adapter_name = "in_app"

    async def deliver(self, db, *, campaign: dict, user: dict, now: datetime) -> dict:
        existing = await db.notification_deliveries.find_one(
            {
                "campaign_id": str(campaign["_id"]),
                "user_id": str(user["_id"]),
                "channel": self.channel,
            }
        )
        if existing and existing.get("status") in {"delivered", "read"}:
            return {
                "status": "delivered",
                "delivery_id": str(existing["_id"]),
                "duplicate": True,
            }

        document = {
            "campaign_id": str(campaign["_id"]),
            "user_id": str(user["_id"]),
            "subject": campaign.get("subject"),
            "message": campaign.get("message"),
            "type": campaign.get("type", "notification"),
            "channel": self.channel,
            "status": "delivered",
            "created_at": now,
            "delivered_at": now,
            "read_at": None,
            "metadata": {
                "campaign_type": campaign.get("type", "notification"),
                "recipient_type": campaign.get("recipient_type"),
                "user_email": user.get("email"),
                "user_type": user.get("user_type"),
            },
        }
        result = await db.notification_deliveries.insert_one(document)
        return {
            "status": "delivered",
            "delivery_id": str(result.inserted_id),
            "duplicate": False,
        }


class EmailNotificationAdapter:
    channel = "email"
    adapter_name = "email"

    async def deliver(self, db, *, campaign: dict, user: dict, now: datetime) -> dict:
        if not settings.smtp_server or not settings.smtp_email or not settings.smtp_password:
            return {
                "status": "failed",
                "failure_reason": "email_adapter_not_configured",
                "delivery_id": None,
                "duplicate": False,
                "metadata": {"recipient_email": user.get("email")},
            }

        return {
            "status": "failed",
            "failure_reason": "email_delivery_not_implemented",
            "delivery_id": None,
            "duplicate": False,
            "metadata": {"recipient_email": user.get("email")},
        }


class SmsNotificationAdapter:
    channel = "sms"
    adapter_name = "sms"

    async def deliver(self, db, *, campaign: dict, user: dict, now: datetime) -> dict:
        if not settings.sms_provider or not settings.sms_api_key or not settings.sms_sender_id:
            return {
                "status": "failed",
                "failure_reason": "sms_adapter_not_configured",
                "delivery_id": None,
                "duplicate": False,
                "metadata": {"recipient_phone": user.get("phone")},
            }

        return {
            "status": "failed",
            "failure_reason": "sms_delivery_not_implemented",
            "delivery_id": None,
            "duplicate": False,
            "metadata": {"recipient_phone": user.get("phone")},
        }


ADAPTERS = {
    "in_app": InAppNotificationAdapter(),
    "email": EmailNotificationAdapter(),
    "sms": SmsNotificationAdapter(),
}


async def _store_failed_delivery(db, *, campaign: dict, user_id: str, channel: str, now: datetime, failure_reason: str | None, metadata: dict | None = None):
    await db.notification_deliveries.insert_one(
        {
            "campaign_id": str(campaign["_id"]),
            "user_id": user_id,
            "subject": campaign.get("subject"),
            "message": campaign.get("message"),
            "type": campaign.get("type", "notification"),
            "channel": channel,
            "status": "failed",
            "created_at": now,
            "delivered_at": None,
            "read_at": None,
            "suppression_reason": None,
            "metadata": metadata or {},
            "failure_reason": failure_reason,
        }
    )


async def process_notification_campaign(
    db,
    *,
    campaign_id: str,
    worker_id: str,
    claimed_campaign: dict | None = None,
    now: datetime | None = None,
) -> dict:
    now = now or _utcnow()
    campaign = claimed_campaign or await db.notification_campaigns.find_one({"_id": _to_object_id(campaign_id, detail="Invalid campaign_id")})
    if not campaign:
      raise ValueError("Notification campaign not found")

    adapter = ADAPTERS.get(campaign.get("channel", "in_app"))
    if not adapter:
        failure_reason = f"unsupported_channel:{campaign.get('channel')}"
        await db.notification_campaigns.update_one(
            {"_id": campaign["_id"]},
            {"$set": {"status": "failed", "failure_reason": failure_reason, "updated_at": now, "last_worker_run_at": now}},
        )
        await append_admin_alert(
            db,
            title="Notification delivery failed",
            message=f"Campaign \"{campaign.get('subject')}\" uses unsupported channel {campaign.get('channel')}.",
            severity="error",
            category="delivery",
            source_reference_type="campaign",
            source_reference_id=str(campaign["_id"]),
            metadata={"failure_reason": failure_reason},
            created_at=now,
        )
        campaign.update({"status": "failed", "failure_reason": failure_reason, "updated_at": now, "last_worker_run_at": now})
        return campaign

    recipients = await list_matching_notification_recipients(
        db,
        recipient_type=campaign.get("recipient_type", "all"),
        recipient_filter=campaign.get("recipient_filter", {}),
        now=now,
    )

    delivered = 0
    suppressed = 0
    failed = 0
    attempts = 0

    from .notifications import _is_notification_allowed_for_user

    for user in recipients:
        attempts += 1
        user_id = str(user["_id"])
        preferences = await get_user_preferences_document(db, user_id=user_id, now=now)
        allowed, suppression_reason = _is_notification_allowed_for_user(campaign, preferences, now=now)

        if not allowed:
            suppressed += 1
            existing = await db.notification_deliveries.find_one(
                {"campaign_id": str(campaign["_id"]), "user_id": user_id, "channel": adapter.channel}
            )
            if not existing:
                await db.notification_deliveries.insert_one(
                    {
                        "campaign_id": str(campaign["_id"]),
                        "user_id": user_id,
                        "subject": campaign.get("subject"),
                        "message": campaign.get("message"),
                        "type": campaign.get("type", "notification"),
                        "channel": adapter.channel,
                        "status": "suppressed",
                        "created_at": now,
                        "delivered_at": None,
                        "read_at": None,
                        "suppression_reason": suppression_reason,
                        "metadata": {"user_email": user.get("email"), "user_type": user.get("user_type")},
                    }
                )
            await append_delivery_attempt(
                db,
                campaign_id=str(campaign["_id"]),
                user_id=user_id,
                channel=adapter.channel,
                adapter=adapter.adapter_name,
                status_value="suppressed",
                failure_reason=suppression_reason,
                metadata={"user_email": user.get("email"), "user_type": user.get("user_type")},
                created_at=now,
            )
            continue

        try:
            result = await adapter.deliver(db, campaign=campaign, user=user, now=now)
            result_status = result.get("status", "delivered")
            result_metadata = result.get("metadata", {})
            failure_reason = result.get("failure_reason")
            if result_status == "delivered":
                delivered += 1
            elif result_status == "failed":
                failed += 1
                await _store_failed_delivery(
                    db,
                    campaign=campaign,
                    user_id=user_id,
                    channel=adapter.channel,
                    now=now,
                    failure_reason=failure_reason,
                    metadata=result_metadata,
                )
            await append_delivery_attempt(
                db,
                campaign_id=str(campaign["_id"]),
                user_id=user_id,
                channel=adapter.channel,
                adapter=adapter.adapter_name,
                status_value=result_status,
                delivery_id=result.get("delivery_id"),
                failure_reason=failure_reason,
                metadata={
                    "duplicate": result.get("duplicate", False),
                    "user_email": user.get("email"),
                    **result_metadata,
                },
                created_at=now,
            )
        except Exception as exc:
            failed += 1
            await _store_failed_delivery(
                db,
                campaign=campaign,
                user_id=user_id,
                channel=adapter.channel,
                now=now,
                failure_reason=str(exc),
                metadata={"error": str(exc), "user_email": user.get("email")},
            )
            await append_delivery_attempt(
                db,
                campaign_id=str(campaign["_id"]),
                user_id=user_id,
                channel=adapter.channel,
                adapter=adapter.adapter_name,
                status_value="failed",
                failure_reason=str(exc),
                metadata={"user_email": user.get("email")},
                created_at=now,
            )

    stats = await refresh_campaign_delivery_stats(db, campaign_id=str(campaign["_id"]), now=now)
    status_value = "failed" if failed and not delivered else "sent"
    failure_reason = None if status_value == "sent" else "delivery_failures"
    await db.notification_campaigns.update_one(
        {"_id": campaign["_id"]},
        {
            "$set": {
                "status": status_value,
                "sent_at": now,
                "updated_at": now,
                "last_worker_run_at": now,
                "failure_reason": failure_reason,
                "worker_lock_id": None,
                "worker_locked_at": None,
                "delivery_stats": stats,
            }
        },
    )

    if failed:
        await append_admin_alert(
            db,
            title="Notification campaign had delivery failures",
            message=f"Campaign \"{campaign.get('subject')}\" finished with {failed} failed delivery attempt(s).",
            severity="warning",
            category="delivery",
            source_reference_type="campaign",
            source_reference_id=str(campaign["_id"]),
            metadata={"failed": failed, "delivered": delivered, "suppressed": suppressed},
            created_at=now,
        )

    updated = await db.notification_campaigns.find_one({"_id": campaign["_id"]})
    updated.setdefault("delivery_stats", stats)
    return updated


async def claim_due_notification_campaigns(db, *, worker_id: str, now: datetime | None = None, limit: int = 10) -> list[dict]:
    now = now or _utcnow()
    claimed = []
    for _ in range(limit):
        campaign = await db.notification_campaigns.find_one_and_update(
            {
                "status": "scheduled",
                "scheduled_for": {"$lte": now},
                "$or": [
                    {"worker_locked_at": None},
                    {"worker_locked_at": {"$exists": False}},
                ],
            },
            {
                "$set": {
                    "status": "processing",
                    "worker_lock_id": worker_id,
                    "worker_locked_at": now,
                    "updated_at": now,
                }
            },
        )
        if not campaign:
            break
        campaign.update({"status": "processing", "worker_lock_id": worker_id, "worker_locked_at": now, "updated_at": now})
        claimed.append(campaign)
    return claimed


async def run_notification_worker_once(db, *, worker_id: str | None = None, now: datetime | None = None, limit: int = 10) -> dict:
    now = now or _utcnow()
    worker_id = worker_id or f"notification-worker:{uuid4()}"
    started_at = now
    claimed_campaigns = 0
    processed_campaigns = 0
    failed_campaigns = 0
    delivery_attempts = 0
    last_error = None
    claimed = []

    try:
        claimed = await claim_due_notification_campaigns(db, worker_id=worker_id, now=now, limit=limit)
        claimed_campaigns = len(claimed)

        for campaign in claimed:
            processed = await process_notification_campaign(
                db,
                campaign_id=str(campaign["_id"]),
                worker_id=worker_id,
                claimed_campaign=campaign,
                now=now,
            )
            processed_campaigns += 1
            stats = processed.get("delivery_stats", {})
            delivery_attempts += int(stats.get("accepted", 0) or 0)
            if processed.get("status") == "failed":
                failed_campaigns += 1

        await record_worker_run(
            db,
            worker_id=worker_id,
            status_value="completed",
            claimed_campaigns=claimed_campaigns,
            processed_campaigns=processed_campaigns,
            failed_campaigns=failed_campaigns,
            delivery_attempts=delivery_attempts,
            metadata={"claimed_campaign_ids": [str(item["_id"]) for item in claimed]},
            started_at=started_at,
            finished_at=_utcnow(),
        )
    except Exception as exc:
        last_error = str(exc)
        await record_worker_run(
            db,
            worker_id=worker_id,
            status_value="failed",
            claimed_campaigns=claimed_campaigns,
            processed_campaigns=processed_campaigns,
            failed_campaigns=failed_campaigns + 1,
            delivery_attempts=delivery_attempts,
            last_error=last_error,
            metadata={"claimed_campaign_ids": [str(item["_id"]) for item in claimed]},
            started_at=started_at,
            finished_at=_utcnow(),
        )
        await append_admin_alert(
            db,
            title="Notification worker run failed",
            message=f"Worker {worker_id} failed: {last_error}",
            severity="error",
            category="worker",
            source_reference_type="worker_run",
            source_reference_id=worker_id,
            metadata={"worker_id": worker_id},
            created_at=_utcnow(),
        )
        raise

    return {
        "worker_id": worker_id,
        "claimed_campaigns": claimed_campaigns,
        "processed_campaigns": processed_campaigns,
        "failed_campaigns": failed_campaigns,
        "delivery_attempts": delivery_attempts,
        "last_error": last_error,
    }


async def notification_worker_loop(get_database_callable, stop_event: asyncio.Event, *, poll_interval_seconds: int = 15):
    while not stop_event.is_set():
        try:
            db = await get_database_callable()
            await run_notification_worker_once(db, worker_id=f"loop:{uuid4()}")
        except Exception:
            pass

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except asyncio.TimeoutError:
            continue