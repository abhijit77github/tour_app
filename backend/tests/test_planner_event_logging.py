import unittest
from copy import deepcopy
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from backend.models.billing import PlannerPricingSettingsUpdate
from backend.routers.admin_billing import save_planner_pricing_settings
from backend.routers.itineraries import create_tourist_itinerary_from_template
from backend.routers.tour_planner import ConfirmRequest, planner_confirm


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
            current = doc.get(key)
            if isinstance(value, dict):
                if "$gte" in value and not (current is not None and current >= value["$gte"]):
                    return False
                continue
            if current != value:
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
                if "$set" in update or "$inc" in update:
                    updated = deepcopy(doc)
                    for key, value in deepcopy(update.get("$inc", {})).items():
                        updated[key] = updated.get(key, 0) + value
                    for key, value in deepcopy(update.get("$set", {})).items():
                        if "." in key:
                            target = updated
                            parts = key.split(".")
                            for part in parts[:-1]:
                                target = target.setdefault(part, {})
                            target[parts[-1]] = value
                        else:
                            updated[key] = value
                    self.docs[index] = updated
                    return FakeUpdateResult(modified_count=1)
                if "$setOnInsert" in update:
                    return FakeUpdateResult(modified_count=0)
                return FakeUpdateResult(modified_count=0)

        if upsert and "$setOnInsert" in update:
            stored = deepcopy(update["$setOnInsert"])
            stored.setdefault("_id", ObjectId())
            self.docs.append(stored)
            return FakeUpdateResult(upserted_id=stored["_id"], modified_count=1)

        return FakeUpdateResult(modified_count=0)


class FakeDB:
    def __init__(self, *, planner_sessions=None, quotes=None, billing_event_log=None, operator_itinerary_templates=None, tourist_itineraries=None, provider_plans=None, credit_ledger=None, admin_settings=None, admin_settings_history=None):
        self.planner_sessions = FakeCollection(planner_sessions)
        self.quotes = FakeCollection(quotes)
        self.billing_event_log = FakeCollection(billing_event_log)
        self.operator_itinerary_templates = FakeCollection(operator_itinerary_templates)
        self.tourist_itineraries = FakeCollection(tourist_itineraries)
        self.provider_plans = FakeCollection(provider_plans)
        self.credit_ledger = FakeCollection(credit_ledger)
        self.admin_settings = FakeCollection(admin_settings)
        self.admin_settings_history = FakeCollection(admin_settings_history)


class PlannerEventLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_confirm_logs_non_billable_qualified_lead_event(self):
        fake_db = FakeDB(
            planner_sessions=[
                {
                    "session_id": "session-1",
                    "user_id": "tourist-1",
                    "requirements": {"locations": ["Manali"]},
                    "suggested_operators": [
                        {
                            "id": "operator-1",
                            "business_name": "Himalayan Escape Co",
                            "serving_areas": ["Manali"],
                            "match_type": "exact",
                            "recommended_service": "tour",
                        }
                    ],
                }
            ]
        )

        with patch("backend.routers.tour_planner.get_database", AsyncMock(return_value=fake_db)):
            response = await planner_confirm(
                ConfirmRequest(session_id="session-1", operator_id="operator-1"),
                current_user={"_id": "tourist-1", "user_type": "tourist"},
            )

        self.assertIn("quote_id", response)
        self.assertEqual(len(fake_db.billing_event_log.docs), 1)
        event = fake_db.billing_event_log.docs[0]
        self.assertEqual(event["source_surface"], "planner")
        self.assertEqual(event["event_type"], "intent_click")
        self.assertEqual(event["source_reference_type"], "planner_session")
        self.assertEqual(event["source_reference_id"], "session-1:operator-1:confirm")
        self.assertEqual(event["outcome_reason"], "planner_quote_intent_created")
        self.assertFalse(event["is_billable"])
        self.assertEqual(event["credits_charged"], 0)
        self.assertEqual(event["metadata"]["operator_name"], "Himalayan Escape Co")
        self.assertEqual(event["metadata"]["configured_credits"], 0)

    async def test_template_save_logs_non_billable_conversion_event(self):
        template_id = ObjectId()
        fake_db = FakeDB(
            operator_itinerary_templates=[
                {
                    "_id": template_id,
                    "status": "published",
                    "operator_profile_id": "operator-1",
                    "title": "Manali Escape",
                    "summary": "Three-day plan",
                    "primary_location": {"area_name": "Manali", "state": "Himachal Pradesh", "country": "India"},
                    "route_locations": [],
                    "duration_days": 3,
                    "trip_styles": ["adventure"],
                    "budget_band": "mid",
                    "notes_for_planner": "Operator template",
                    "days": [],
                }
            ]
        )

        with patch("backend.routers.itineraries.get_database", AsyncMock(return_value=fake_db)):
            response = await create_tourist_itinerary_from_template(
                str(template_id),
                current_user={"_id": "tourist-1", "user_type": "tourist"},
            )

        self.assertEqual(response["message"], "Itinerary created from template")
        self.assertEqual(len(fake_db.billing_event_log.docs), 1)
        event = fake_db.billing_event_log.docs[0]
        itinerary_id = response["itinerary"]["_id"]
        self.assertEqual(event["source_surface"], "planner")
        self.assertEqual(event["event_type"], "conversion")
        self.assertEqual(event["source_reference_type"], "itinerary_template")
        self.assertEqual(event["source_reference_id"], itinerary_id)
        self.assertEqual(event["outcome_reason"], "template_itinerary_saved")
        self.assertFalse(event["is_billable"])
        self.assertEqual(event["credits_charged"], 0)
        self.assertEqual(event["metadata"]["template_id"], str(template_id))
        self.assertEqual(event["metadata"]["configured_credits"], 0)

    async def test_planner_confirm_uses_configured_credits_when_enabled(self):
        fake_db = FakeDB(
            planner_sessions=[
                {
                    "session_id": "session-credits",
                    "user_id": "tourist-1",
                    "requirements": {"locations": ["Manali"]},
                    "suggested_operators": [
                        {
                            "id": "operator-1",
                            "business_name": "Himalayan Escape Co",
                            "serving_areas": ["Manali"],
                            "match_type": "exact",
                            "recommended_service": "tour",
                        }
                    ],
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "operator-1",
                    "plan_status": "active",
                    "credits_remaining": 5,
                }
            ],
            admin_settings=[
                {
                    "key": "planner_billing",
                    "value": {
                        "search_profile_click": 0,
                        "planner_intent_click": 2,
                        "qualified_lead": 0,
                        "conversion": 0,
                    },
                }
            ],
        )

        with patch("backend.routers.tour_planner.get_database", AsyncMock(return_value=fake_db)):
            response = await planner_confirm(
                ConfirmRequest(session_id="session-credits", operator_id="operator-1"),
                current_user={"_id": "tourist-1", "user_type": "tourist"},
            )

        self.assertIn("quote_id", response)
        self.assertEqual(fake_db.provider_plans.docs[0]["credits_remaining"], 3)
        self.assertEqual(len(fake_db.credit_ledger.docs), 1)
        self.assertEqual(fake_db.credit_ledger.docs[0]["credits_delta"], -2)
        event = fake_db.billing_event_log.docs[0]
        self.assertEqual(fake_db.credit_ledger.docs[0]["billing_event_idempotency_key"], event["idempotency_key"])
        self.assertTrue(event["is_billable"])
        self.assertEqual(event["credits_charged"], 2)
        self.assertEqual(event["metadata"]["configured_credits"], 2)
        self.assertEqual(event["outcome_reason"], "planner_quote_intent_created")

    async def test_save_planner_pricing_records_audit_history(self):
        fake_db = FakeDB(
            admin_settings=[
                {
                    "key": "planner_billing",
                    "value": {"search_profile_click": 0, "planner_intent_click": 0, "qualified_lead": 0, "conversion": 0},
                    "updated_by": "admin-old",
                }
            ]
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await save_planner_pricing_settings(
                PlannerPricingSettingsUpdate(search_profile_click=1, planner_intent_click=2, qualified_lead=0, conversion=0),
                admin={"_id": "admin-1"},
            )

        self.assertEqual(response["settings"]["values"], {"search_profile_click": 1, "planner_intent_click": 2, "qualified_lead": 0, "conversion": 0})
        self.assertEqual(len(fake_db.admin_settings_history.docs), 1)
        history = fake_db.admin_settings_history.docs[0]
        self.assertEqual(history["key"], "planner_billing")
        self.assertEqual(history["previous_value"], {"search_profile_click": 0, "planner_intent_click": 0, "qualified_lead": 0, "conversion": 0})
        self.assertEqual(history["new_value"], {"search_profile_click": 1, "planner_intent_click": 2, "qualified_lead": 0, "conversion": 0})
        self.assertEqual(history["changed_by"], "admin-1")


if __name__ == "__main__":
    unittest.main()