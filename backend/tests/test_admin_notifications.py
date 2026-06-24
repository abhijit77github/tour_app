import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException

from backend.utils.notification_delivery import run_notification_worker_once
from backend.utils.notifications import (
    create_notification_campaign,
    create_notification_template,
    delete_notification_template,
    get_notification_preferences,
    get_user_notification_summary,
    mark_notification_delivery_as_read,
    preview_notification_audience,
    update_notification_preferences,
)


class FakeCursor:
    def __init__(self, docs):
        self.docs = [deepcopy(doc) for doc in docs]

    async def to_list(self, length=None):
        if length is None:
            return [deepcopy(doc) for doc in self.docs]
        return [deepcopy(doc) for doc in self.docs[:length]]


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeDeleteResult:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count


class FakeUpdateResult:
    def __init__(self, modified_count=0):
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in (docs or [])]

    def _value_matches(self, current, expected):
        if isinstance(expected, dict):
            if "$lte" in expected and not (current is not None and current <= expected["$lte"]):
                return False
            if "$exists" in expected:
                exists = current is not None
                if exists != expected["$exists"]:
                    return False
            return True
        return current == expected

    def _matches(self, doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(self._matches(doc, item) for item in value):
                    return False
                continue
            if not self._value_matches(doc.get(key), value):
                return False
        return True

    def find(self, query):
        if not query:
            return FakeCursor(self.docs)
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query):
        for doc in self.docs:
            if self._matches(doc, query):
                return deepcopy(doc)
        return None

    async def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)
        return FakeInsertResult(stored["_id"])

    async def update_one(self, query, update, upsert=False):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                updated = deepcopy(doc)
                for key, value in deepcopy(update.get("$set", {})).items():
                    updated[key] = value
                self.docs[index] = updated
                return FakeUpdateResult(modified_count=1)
        return FakeUpdateResult(modified_count=0)

    async def update_many(self, query, update):
        modified_count = 0
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                updated = deepcopy(doc)
                for key, value in deepcopy(update.get("$set", {})).items():
                    updated[key] = value
                self.docs[index] = updated
                modified_count += 1
        return FakeUpdateResult(modified_count=modified_count)

    async def find_one_and_update(self, query, update):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                updated = deepcopy(doc)
                for key, value in deepcopy(update.get("$set", {})).items():
                    updated[key] = value
                self.docs[index] = updated
                return deepcopy(doc)
        return None

    async def delete_one(self, query):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                self.docs.pop(index)
                return FakeDeleteResult(deleted_count=1)
        return FakeDeleteResult(deleted_count=0)


class FakeDB:
    def __init__(
        self,
        *,
        users=None,
        notification_templates=None,
        notification_campaigns=None,
        notification_audit_log=None,
        notification_deliveries=None,
        notification_delivery_attempts=None,
        notification_preferences=None,
        notification_worker_runs=None,
        admin_alerts=None,
    ):
        self.users = FakeCollection(users)
        self.notification_templates = FakeCollection(notification_templates)
        self.notification_campaigns = FakeCollection(notification_campaigns)
        self.notification_audit_log = FakeCollection(notification_audit_log)
        self.notification_deliveries = FakeCollection(notification_deliveries)
        self.notification_delivery_attempts = FakeCollection(notification_delivery_attempts)
        self.notification_preferences = FakeCollection(notification_preferences)
        self.notification_worker_runs = FakeCollection(notification_worker_runs)
        self.admin_alerts = FakeCollection(admin_alerts)


class AdminNotificationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_notification_audience_filters_active_tourists(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        fake_db = FakeDB(
            users=[
                {"_id": "t1", "user_type": "tourist", "is_active": True, "last_login": now - timedelta(days=2)},
                {"_id": "t2", "user_type": "tourist", "is_active": False, "last_login": now - timedelta(days=1)},
                {"_id": "o1", "user_type": "operator", "is_active": True, "last_login": now - timedelta(days=1)},
            ]
        )

        preview = await preview_notification_audience(
            fake_db,
            recipient_type="tourists",
            recipient_filter={"active_only": True, "last_active_days": 7},
            now=now,
        )

        self.assertEqual(preview["estimated_recipients"], 1)
        self.assertEqual(preview["breakdown"]["tourists"], 1)
        self.assertEqual(preview["breakdown"]["operators"], 0)

    async def test_immediate_campaign_creates_in_app_deliveries(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        fake_db = FakeDB(
            users=[
                {"_id": "t1", "user_type": "tourist", "is_active": True, "last_login": now - timedelta(days=1), "email": "t1@test.local"},
                {"_id": "t2", "user_type": "tourist", "is_active": True, "last_login": now - timedelta(days=2), "email": "t2@test.local"},
            ]
        )

        campaign = await create_notification_campaign(
            fake_db,
            {
                "type": "announcement",
                "subject": "Planner update",
                "message": "Planner quota visibility is now live.",
                "channel": "in_app",
                "recipient_type": "tourists",
                "recipient_filter": {"active_only": True},
                "send_now": True,
                "scheduled_for": None,
            },
            admin={"_id": "admin-1", "email": "admin@tourapp.local", "full_name": "Admin"},
            now=now,
        )

        self.assertEqual(campaign["status"], "sent")
        self.assertEqual(campaign["delivery_stats"]["delivered"], 2)
        self.assertEqual(len(fake_db.notification_deliveries.docs), 2)
        self.assertEqual(len(fake_db.notification_delivery_attempts.docs), 2)

    async def test_worker_processes_scheduled_campaign(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        campaign_id = ObjectId()
        fake_db = FakeDB(
            users=[
                {"_id": "o1", "user_type": "operator", "is_active": True, "last_login": now, "email": "o1@test.local"},
                {"_id": "o2", "user_type": "operator", "is_active": True, "last_login": now, "email": "o2@test.local"},
            ],
            notification_campaigns=[
                {
                    "_id": campaign_id,
                    "type": "alert",
                    "subject": "Maintenance",
                    "message": "Downtime tonight.",
                    "channel": "in_app",
                    "recipient_type": "operators",
                    "recipient_filter": {"active_only": True},
                    "recipient_count": 2,
                    "status": "scheduled",
                    "scheduled_for": now - timedelta(minutes=1),
                    "sent_at": None,
                    "created_at": now - timedelta(minutes=2),
                    "updated_at": now - timedelta(minutes=2),
                    "delivery_stats": {"accepted": 0, "delivered": 0, "opened": 0, "clicked": 0, "failed": 0, "suppressed": 0, "read": 0},
                    "worker_lock_id": None,
                    "worker_locked_at": None,
                    "last_worker_run_at": None,
                    "failure_reason": None,
                }
            ],
        )

        result = await run_notification_worker_once(fake_db, worker_id="worker-1", now=now)

        self.assertEqual(result["processed_campaigns"], 1)
        self.assertEqual(len(fake_db.notification_deliveries.docs), 2)
        self.assertEqual(fake_db.notification_campaigns.docs[0]["status"], "sent")
        self.assertEqual(len(fake_db.notification_worker_runs.docs), 1)

    async def test_quiet_hours_suppresses_delivery(self):
        now = datetime(2026, 6, 10, 23, 0, tzinfo=timezone.utc)
        fake_db = FakeDB(
            users=[
                {"_id": "t1", "user_type": "tourist", "is_active": True, "last_login": now, "email": "t1@test.local"},
            ],
            notification_preferences=[
                {
                    "user_id": "t1",
                    "preferences": {
                        "in_app_enabled": True,
                        "marketing_enabled": True,
                        "announcements_enabled": True,
                        "alerts_enabled": True,
                        "quiet_hours_enabled": True,
                        "quiet_hours_start": "22:00",
                        "quiet_hours_end": "06:00",
                        "timezone": "UTC",
                    },
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        )

        campaign = await create_notification_campaign(
            fake_db,
            {
                "type": "notification",
                "subject": "New deal",
                "message": "A new deal is available.",
                "channel": "in_app",
                "recipient_type": "tourists",
                "recipient_filter": {"active_only": True},
                "send_now": True,
                "scheduled_for": None,
            },
            admin={"_id": "admin-1", "email": "admin@tourapp.local", "full_name": "Admin"},
            now=now,
        )

        self.assertEqual(campaign["delivery_stats"]["suppressed"], 1)
        self.assertEqual(fake_db.notification_deliveries.docs[0]["status"], "suppressed")
        summary = await get_user_notification_summary(fake_db, user_id="t1")
        self.assertEqual(summary["unread_count"], 0)

    async def test_mark_notification_read_updates_user_summary(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        delivery_id = ObjectId()
        campaign_id = str(ObjectId())
        fake_db = FakeDB(
            notification_deliveries=[
                {
                    "_id": delivery_id,
                    "campaign_id": campaign_id,
                    "user_id": "t1",
                    "subject": "Welcome",
                    "message": "Welcome aboard",
                    "type": "announcement",
                    "channel": "in_app",
                    "status": "delivered",
                    "created_at": now,
                    "delivered_at": now,
                    "read_at": None,
                    "metadata": {},
                }
            ],
            notification_campaigns=[
                {
                    "_id": ObjectId(campaign_id),
                    "status": "sent",
                    "delivery_stats": {"accepted": 1, "delivered": 1, "opened": 0, "clicked": 0, "failed": 0, "suppressed": 0, "read": 0},
                }
            ],
        )

        item = await mark_notification_delivery_as_read(fake_db, delivery_id=str(delivery_id), user_id="t1", now=now)

        self.assertIsNotNone(item["read_at"])
        summary = await get_user_notification_summary(fake_db, user_id="t1")
        self.assertEqual(summary["unread_count"], 0)

    async def test_delete_template_blocks_when_referenced_by_campaign(self):
        template_id = ObjectId()
        fake_db = FakeDB(
            notification_templates=[
                {
                    "_id": template_id,
                    "name": "Operator update",
                    "category": "Announcement",
                    "subject": "Update",
                    "message": "Message",
                }
            ],
            notification_campaigns=[
                {
                    "_id": ObjectId(),
                    "template_id": str(template_id),
                    "subject": "Sent from template",
                }
            ],
        )

        with self.assertRaises(HTTPException) as exc_info:
            await delete_notification_template(
                fake_db,
                str(template_id),
                admin={"_id": "admin-1", "email": "admin@tourapp.local"},
            )

        self.assertEqual(exc_info.exception.status_code, 409)

    async def test_preferences_round_trip(self):
        fake_db = FakeDB()

        initial = await get_notification_preferences(fake_db, user_id="u1")
        self.assertTrue(initial["preferences"]["in_app_enabled"])

        updated = await update_notification_preferences(
            fake_db,
            user_id="u1",
            payload={"marketing_enabled": False, "timezone": "Asia/Kolkata"},
        )
        self.assertFalse(updated["preferences"]["marketing_enabled"])
        self.assertEqual(updated["preferences"]["timezone"], "Asia/Kolkata")

    async def test_create_template_persists_document(self):
        fake_db = FakeDB()

        template = await create_notification_template(
            fake_db,
            {
                "name": "Welcome tourists",
                "category": "Welcome",
                "subject": "Welcome",
                "message": "Thanks for joining Tour App.",
                "channels": ["in_app"],
                "is_active": True,
            },
            admin={"_id": "admin-1", "email": "admin@tourapp.local"},
        )

        self.assertEqual(template["name"], "Welcome tourists")
        self.assertEqual(len(fake_db.notification_templates.docs), 1)
        self.assertEqual(len(fake_db.notification_audit_log.docs), 1)


if __name__ == "__main__":
    unittest.main()
