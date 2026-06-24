import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from backend.routers.tour_planner import ChatRequest, planner_chat
from backend.utils.planner_quota import (
    consume_tourist_planner_request_quota,
    get_tourist_planner_quota_status,
    grant_tourist_planner_reward,
)


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, upserted_id=None, modified_count=0):
        self.upserted_id = upserted_id
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in (docs or [])]

    @staticmethod
    def _matches(doc, query):
        for key, value in query.items():
            if doc.get(key) != value:
                return False
        return True

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
                for key, value in deepcopy(update.get("$inc", {})).items():
                    updated[key] = updated.get(key, 0) + value
                for key, value in deepcopy(update.get("$set", {})).items():
                    updated[key] = value
                self.docs[index] = updated
                return FakeUpdateResult(modified_count=1)

        if upsert and "$setOnInsert" in update:
            stored = deepcopy(update["$setOnInsert"])
            stored.setdefault("_id", ObjectId())
            self.docs.append(stored)
            return FakeUpdateResult(upserted_id=stored["_id"], modified_count=1)

        return FakeUpdateResult(modified_count=0)

    async def find_one_and_update(self, query, update, return_document=None):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                updated = deepcopy(doc)
                for key, value in deepcopy(update.get("$inc", {})).items():
                    updated[key] = updated.get(key, 0) + value
                for key, value in deepcopy(update.get("$set", {})).items():
                    updated[key] = value
                self.docs[index] = updated
                return deepcopy(updated)
        return None


class FakeDB:
    def __init__(
        self,
        *,
        admin_settings=None,
        tourist_planner_quotas=None,
        tourist_planner_quota_ledger=None,
        tourist_planner_reward_events=None,
        tourist_planner_reward_verifications=None,
    ):
        self.admin_settings = FakeCollection(admin_settings)
        self.tourist_planner_quotas = FakeCollection(tourist_planner_quotas)
        self.tourist_planner_quota_ledger = FakeCollection(tourist_planner_quota_ledger)
        self.tourist_planner_reward_events = FakeCollection(tourist_planner_reward_events)
        self.tourist_planner_reward_verifications = FakeCollection(tourist_planner_reward_verifications)


class PlannerQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_daily_rollover_resets_daily_usage_but_keeps_month_usage(self):
        fake_db = FakeDB(
            tourist_planner_quotas=[
                {
                    "user_id": "tourist-1",
                    "day_key": "2026-06-09",
                    "month_key": "2026-06",
                    "used_today": 3,
                    "used_this_month": 9,
                    "bonus_daily_credits": 1,
                    "bonus_monthly_credits": 2,
                }
            ]
        )

        result = await consume_tourist_planner_request_quota(
            fake_db,
            user_id="tourist-1",
            session_id="session-1",
            current_time=datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(result["allowed"])
        self.assertEqual(result["quota"]["used_today"], 1)
        self.assertEqual(result["quota"]["used_this_month"], 10)
        self.assertEqual(result["quota"]["bonus_daily_credits"], 0)
        self.assertEqual(result["quota"]["bonus_monthly_credits"], 2)

    async def test_monthly_rollover_resets_month_usage_and_bonuses(self):
        fake_db = FakeDB(
            tourist_planner_quotas=[
                {
                    "user_id": "tourist-1",
                    "day_key": "2026-05-31",
                    "month_key": "2026-05",
                    "used_today": 2,
                    "used_this_month": 12,
                    "bonus_daily_credits": 1,
                    "bonus_monthly_credits": 4,
                }
            ]
        )

        result = await consume_tourist_planner_request_quota(
            fake_db,
            user_id="tourist-1",
            session_id="session-2",
            current_time=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(result["allowed"])
        self.assertEqual(result["quota"]["used_today"], 1)
        self.assertEqual(result["quota"]["used_this_month"], 1)
        self.assertEqual(result["quota"]["bonus_daily_credits"], 0)
        self.assertEqual(result["quota"]["bonus_monthly_credits"], 0)

    async def test_reward_must_be_verified_and_duplicate_reward_is_blocked(self):
        fake_db = FakeDB(
            tourist_planner_reward_verifications=[
                {
                    "_id": ObjectId(),
                    "user_id": "tourist-1",
                    "reward_id": "reward-1",
                    "reward_type": "ad",
                    "status": "verified",
                }
            ]
        )

        first = await grant_tourist_planner_reward(
            fake_db,
            user_id="tourist-1",
            reward_id="reward-1",
            reward_type="ad",
            current_time=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        )
        second = await grant_tourist_planner_reward(
            fake_db,
            user_id="tourist-1",
            reward_id="reward-1",
            reward_type="ad",
            current_time=datetime(2026, 6, 10, 10, 5, tzinfo=timezone.utc),
        )
        blocked = await grant_tourist_planner_reward(
            fake_db,
            user_id="tourist-1",
            reward_id="reward-2",
            reward_type="promotion",
            current_time=datetime(2026, 6, 10, 10, 6, tzinfo=timezone.utc),
        )

        self.assertTrue(first["granted"])
        self.assertFalse(second["granted"])
        self.assertEqual(second["reason"], "duplicate_reward")
        self.assertFalse(blocked["granted"])
        self.assertEqual(blocked["reason"], "reward_not_verified")
        status = await get_tourist_planner_quota_status(
            fake_db,
            user_id="tourist-1",
            current_time=datetime(2026, 6, 10, 10, 7, tzinfo=timezone.utc),
        )
        self.assertEqual(status["quota"]["bonus_daily_credits"], 1)
        self.assertEqual(status["quota"]["bonus_monthly_credits"], 1)
        self.assertEqual(len(fake_db.tourist_planner_quota_ledger.docs), 1)

    async def test_planner_chat_blocks_before_bedrock_when_quota_exhausted(self):
        fake_db = FakeDB(
            tourist_planner_quotas=[
                {
                    "user_id": "tourist-1",
                    "day_key": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "month_key": datetime.now(timezone.utc).strftime("%Y-%m"),
                    "used_today": 3,
                    "used_this_month": 3,
                    "bonus_daily_credits": 0,
                    "bonus_monthly_credits": 0,
                }
            ]
        )

        with patch("backend.routers.tour_planner.get_database", AsyncMock(return_value=fake_db)), patch(
            "backend.routers.tour_planner.get_bedrock_client",
            side_effect=AssertionError("Bedrock should not be called when quota is exhausted"),
        ):
            with self.assertRaises(HTTPException) as exc_info:
                await planner_chat(
                    ChatRequest(session_id="session-blocked", message="Plan me a trip to Manali"),
                    current_user={"_id": "tourist-1", "user_type": "tourist"},
                )

        self.assertEqual(exc_info.exception.status_code, 429)
        self.assertEqual(exc_info.exception.detail["message"], "Planner request limit reached")


if __name__ == "__main__":
    unittest.main()