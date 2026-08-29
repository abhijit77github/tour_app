import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.utils.billing import build_click_idempotency_key, build_planner_impression_source_reference


class BillingPolicyControlsTests(unittest.TestCase):
    def test_click_dedupe_session_first_ignores_request_id_changes(self):
        now = datetime(2026, 8, 29, 12, 5, 0, tzinfo=timezone.utc)
        with patch("backend.utils.billing.settings.billing_search_click_dedupe_minutes", 30), patch(
            "backend.utils.billing.settings.billing_search_click_identity_mode", "session_first"
        ):
            key_1 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-1",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=now,
            )
            key_2 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-2",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=now,
            )

        self.assertEqual(key_1, key_2)

    def test_click_dedupe_request_first_uses_request_id(self):
        now = datetime(2026, 8, 29, 12, 5, 0, tzinfo=timezone.utc)
        with patch("backend.utils.billing.settings.billing_search_click_dedupe_minutes", 30), patch(
            "backend.utils.billing.settings.billing_search_click_identity_mode", "request_first"
        ):
            key_1 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-1",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=now,
            )
            key_2 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-2",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=now,
            )

        self.assertNotEqual(key_1, key_2)

    def test_click_dedupe_minutes_changes_bucket_behavior(self):
        t1 = datetime(2026, 8, 29, 12, 1, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 29, 12, 4, 0, tzinfo=timezone.utc)

        with patch("backend.utils.billing.settings.billing_search_click_dedupe_minutes", 5), patch(
            "backend.utils.billing.settings.billing_search_click_identity_mode", "session_first"
        ):
            key_1 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-1",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=t1,
            )
            key_2 = build_click_idempotency_key(
                promotion_id="promo-1",
                source="search",
                session_id="sess-1",
                request_id="req-2",
                client_host="127.0.0.1",
                user_agent="ua",
                current_time=t2,
            )

        self.assertEqual(key_1, key_2)

    def test_planner_impression_scope_session(self):
        with patch("backend.utils.billing.settings.billing_planner_impression_scope", "session"):
            key = build_planner_impression_source_reference(session_id="sess-2", operator_profile_id="op-2")
        self.assertEqual(key, "sess-2:op-2:impression")

    def test_planner_impression_scope_daily(self):
        now = datetime(2026, 8, 29, 8, 0, 0, tzinfo=timezone.utc)
        with patch("backend.utils.billing.settings.billing_planner_impression_scope", "daily"):
            key = build_planner_impression_source_reference(
                session_id="sess-2",
                operator_profile_id="op-2",
                current_time=now,
            )
        self.assertEqual(key, "sess-2:op-2:impression:20260829")

    def test_planner_impression_scope_request(self):
        with patch("backend.utils.billing.settings.billing_planner_impression_scope", "request"):
            key = build_planner_impression_source_reference(
                session_id="sess-2",
                operator_profile_id="op-2",
                request_key="req-77",
            )
        self.assertEqual(key, "sess-2:op-2:impression:req-77")


if __name__ == "__main__":
    unittest.main()
