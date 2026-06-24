import unittest
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import get_database
from backend.routers.admin import get_current_admin
from backend import routers as backend_routers
from backend.routers.admin_notifications import router as admin_notifications_router
from backend.routers.auth import get_current_user
from backend.routers.user_notifications import router as user_notifications_router
from backend.tests.test_admin_notifications import FakeDB


def build_test_client(*, db, admin=None, user=None):
    app = FastAPI()
    app.include_router(admin_notifications_router)
    app.include_router(user_notifications_router)

    async def override_db():
        return db

    async def override_admin():
        return admin or {"_id": "admin-1", "email": "admin@tourapp.local", "full_name": "Admin", "role": "super_admin"}

    async def override_user():
        return user or {"_id": "tourist-1", "email": "tourist1@tourapp.local", "full_name": "Tourist One", "user_type": "tourist"}

    app.dependency_overrides[get_database] = override_db
    app.dependency_overrides[get_current_admin] = override_admin
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app)


@contextmanager
def patched_router_database(db):
    async def override_db():
        return db

    with patch.object(backend_routers.admin_notifications, "get_database", override_db), patch.object(backend_routers.user_notifications, "get_database", override_db):
        yield


class NotificationRouterApiTests(unittest.TestCase):
    def test_admin_campaign_create_endpoint_fans_out_in_app_deliveries(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        fake_db = FakeDB(
            users=[
                {"_id": "tourist-1", "user_type": "tourist", "is_active": True, "last_login": now, "email": "tourist1@tourapp.local"},
                {"_id": "tourist-2", "user_type": "tourist", "is_active": True, "last_login": now - timedelta(hours=2), "email": "tourist2@tourapp.local"},
            ]
        )
        client = build_test_client(db=fake_db)

        with patched_router_database(fake_db):
            response = client.post(
                "/admin/notifications/campaigns",
                json={
                    "type": "announcement",
                    "subject": "System update",
                    "message": "Planner quota is live.",
                    "channel": "in_app",
                    "recipient_type": "tourists",
                    "recipient_filter": {"active_only": True},
                    "send_now": True,
                    "scheduled_for": None,
                },
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["campaign"]["status"], "sent")
        self.assertEqual(body["campaign"]["delivery_stats"]["delivered"], 2)
        self.assertEqual(len(fake_db.notification_deliveries.docs), 2)
        self.assertEqual(len(fake_db.notification_delivery_attempts.docs), 2)

    def test_admin_campaign_create_endpoint_records_email_adapter_failure(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        fake_db = FakeDB(
            users=[
                {"_id": "tourist-1", "user_type": "tourist", "is_active": True, "last_login": now, "email": "tourist1@tourapp.local"},
            ]
        )
        client = build_test_client(db=fake_db)

        with patched_router_database(fake_db):
            response = client.post(
                "/admin/notifications/campaigns",
                json={
                    "type": "announcement",
                    "subject": "Email scaffold",
                    "message": "This exercises the email adapter contract.",
                    "channel": "email",
                    "recipient_type": "tourists",
                    "recipient_filter": {"active_only": True},
                    "send_now": True,
                    "scheduled_for": None,
                },
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["campaign"]["channel"], "email")
        self.assertEqual(body["campaign"]["status"], "failed")
        self.assertEqual(body["campaign"]["failure_reason"], "delivery_failures")
        self.assertEqual(len(fake_db.notification_delivery_attempts.docs), 1)
        self.assertEqual(fake_db.notification_delivery_attempts.docs[0]["adapter"], "email")
        self.assertEqual(fake_db.notification_delivery_attempts.docs[0]["failure_reason"], "email_adapter_not_configured")

    def test_admin_alert_and_worker_endpoints_return_http_results(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        campaign_id = ObjectId()
        alert_id = ObjectId()
        fake_db = FakeDB(
            users=[
                {"_id": "operator-1", "user_type": "operator", "is_active": True, "last_login": now, "email": "operator1@tourapp.local"},
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
                    "recipient_count": 1,
                    "status": "scheduled",
                    "scheduled_for": now - timedelta(minutes=5),
                    "sent_at": None,
                    "created_at": now - timedelta(minutes=10),
                    "updated_at": now - timedelta(minutes=10),
                    "delivery_stats": {"accepted": 0, "delivered": 0, "opened": 0, "clicked": 0, "failed": 0, "suppressed": 0, "read": 0},
                    "worker_lock_id": None,
                    "worker_locked_at": None,
                    "last_worker_run_at": None,
                    "failure_reason": None,
                }
            ],
            admin_alerts=[
                {
                    "_id": alert_id,
                    "title": "Worker attention needed",
                    "message": "A scheduled campaign is due.",
                    "severity": "warning",
                    "category": "worker",
                    "service": "notification",
                    "read": False,
                    "read_at": None,
                    "created_at": now - timedelta(minutes=2),
                    "source_reference_type": "campaign",
                    "source_reference_id": str(campaign_id),
                    "metadata": {},
                }
            ],
        )
        client = build_test_client(db=fake_db, user={"_id": "operator-1", "email": "operator1@tourapp.local", "full_name": "Operator One", "user_type": "operator"})

        with patched_router_database(fake_db):
            summary_response = client.get("/admin/notifications/summary")
            self.assertEqual(summary_response.status_code, 200)
            self.assertEqual(summary_response.json()["admin_alerts"]["unread_count"], 1)

            alerts_response = client.get("/admin/notifications/alerts")
            self.assertEqual(alerts_response.status_code, 200)
            self.assertEqual(len(alerts_response.json()["alerts"]), 1)

            read_response = client.post(f"/admin/notifications/alerts/{alert_id}/read")
            self.assertEqual(read_response.status_code, 200)
            self.assertTrue(read_response.json()["alert"]["read"])

            worker_response = client.post("/admin/notifications/worker-runs/trigger")
            self.assertEqual(worker_response.status_code, 200)
            self.assertEqual(worker_response.json()["result"]["processed_campaigns"], 1)
            self.assertEqual(len(fake_db.notification_worker_runs.docs), 1)
            self.assertEqual(fake_db.notification_campaigns.docs[0]["status"], "sent")

    def test_user_inbox_and_mark_read_endpoints_work_over_http(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        delivery_id = ObjectId()
        campaign_id = ObjectId()
        fake_db = FakeDB(
            notification_deliveries=[
                {
                    "_id": delivery_id,
                    "campaign_id": str(campaign_id),
                    "user_id": "tourist-1",
                    "subject": "Welcome",
                    "message": "Your first notification",
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
                    "_id": campaign_id,
                    "status": "sent",
                    "delivery_stats": {"accepted": 1, "delivered": 1, "opened": 0, "clicked": 0, "failed": 0, "suppressed": 0, "read": 0},
                }
            ],
        )
        client = build_test_client(db=fake_db)

        with patched_router_database(fake_db):
            summary_response = client.get("/notifications/summary")
            self.assertEqual(summary_response.status_code, 200)
            self.assertEqual(summary_response.json()["unread_count"], 1)

            inbox_response = client.get("/notifications/inbox")
            self.assertEqual(inbox_response.status_code, 200)
            self.assertEqual(len(inbox_response.json()["items"]), 1)

            read_response = client.post(f"/notifications/inbox/{delivery_id}/read")
            self.assertEqual(read_response.status_code, 200)
            self.assertIsNotNone(read_response.json()["item"]["read_at"])

            post_read_summary = client.get("/notifications/summary")
            self.assertEqual(post_read_summary.status_code, 200)
            self.assertEqual(post_read_summary.json()["unread_count"], 0)

    def test_user_preferences_endpoints_round_trip_over_http(self):
        fake_db = FakeDB()
        client = build_test_client(db=fake_db)

        with patched_router_database(fake_db):
            initial_response = client.get("/notifications/preferences")
            self.assertEqual(initial_response.status_code, 200)
            self.assertTrue(initial_response.json()["preferences"]["in_app_enabled"])

            update_response = client.put(
                "/notifications/preferences",
                json={
                    "in_app_enabled": True,
                    "marketing_enabled": False,
                    "announcements_enabled": True,
                    "alerts_enabled": True,
                    "quiet_hours_enabled": True,
                    "quiet_hours_start": "22:00",
                    "quiet_hours_end": "06:00",
                    "timezone": "Asia/Kolkata",
                },
            )
            self.assertEqual(update_response.status_code, 200)
            self.assertFalse(update_response.json()["preferences"]["marketing_enabled"])
            self.assertEqual(update_response.json()["preferences"]["timezone"], "Asia/Kolkata")


if __name__ == "__main__":
    unittest.main()