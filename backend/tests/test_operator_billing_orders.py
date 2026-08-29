import unittest
import hmac
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from backend.routers import operator_billing as operator_billing_router_module
from backend.routers.operator_billing import cancel_operator_billing_order, create_operator_billing_order, update_operator_plan_order_payment_state
from backend.routers.admin_billing import (
    apply_refund_compensation,
    complete_plan_order,
    expire_stale_orders,
    export_credit_reconciliation_issues,
    get_credit_reconciliation_anomalies,
    get_billing_webhook_event,
    list_billing_webhook_events,
    reconcile_credit_events,
    repair_reconciliation_credit_events,
    reprocess_billing_webhook_event,
)
from backend.models.billing import OperatorPlanOrderCreateRequest, PlanOrderPaymentStateUpdateRequest, PlanOrderSettlementRequest, RefundCreditCompensationRequest
from backend.utils.billing import assign_plan_to_operator, complete_operator_plan_order, create_operator_plan_order, expire_stale_plan_orders


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, modified_count=0, upserted_id=None):
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in (docs or [])]

    @staticmethod
    def _matches(doc, query):
        for key, value in query.items():
            current = doc.get(key)
            if isinstance(value, dict):
                if "$in" in value and current not in value["$in"]:
                    return False
                if "$ne" in value and current == value["$ne"]:
                    return False
                if "$lt" in value and not (current is not None and current < value["$lt"]):
                    return False
                if "$exists" in value:
                    exists = key in doc
                    if exists != bool(value["$exists"]):
                        return False
                continue
            if current != value:
                return False
        return True

    async def find_one(self, query, sort=None):
        matched = [deepcopy(doc) for doc in self.docs if self._matches(doc, query)]
        if sort and matched:
            for field, direction in reversed(sort):
                reverse = direction == -1
                matched.sort(key=lambda row: row.get(field), reverse=reverse)
        return matched[0] if matched else None

    def find(self, query):
        matched = [deepcopy(doc) for doc in self.docs if self._matches(doc, query)]

        class _FindResult:
            def __init__(self, rows):
                self._rows = rows

            def sort(self, sort_spec):
                for key, direction in reversed(sort_spec):
                    reverse = direction == -1
                    self._rows.sort(key=lambda row: row.get(key), reverse=reverse)
                return self

            def limit(self, n):
                if n is not None:
                    self._rows = self._rows[:n]
                return self

            async def to_list(self, length=None):
                if length is None:
                    return deepcopy(self._rows)
                return deepcopy(self._rows[:length])

        return _FindResult(matched)

    async def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)
        return FakeInsertResult(stored["_id"])

    async def update_one(self, query, update, upsert=False):
        for idx, doc in enumerate(self.docs):
            if not self._matches(doc, query):
                continue
            updated = deepcopy(doc)
            for key, value in update.get("$inc", {}).items():
                updated[key] = updated.get(key, 0) + value
            for key, value in update.get("$set", {}).items():
                if "." in key:
                    target = updated
                    parts = key.split(".")
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = value
                else:
                    updated[key] = value
            for key, value in update.get("$push", {}).items():
                updated.setdefault(key, [])
                updated[key].append(value)
            self.docs[idx] = updated
            return FakeUpdateResult(modified_count=1)
        if upsert:
            created = deepcopy(query)
            for key, value in update.get("$setOnInsert", {}).items():
                created[key] = value
            for key, value in update.get("$set", {}).items():
                created[key] = value
            inserted_id = created.setdefault("_id", ObjectId())
            self.docs.append(created)
            return FakeUpdateResult(modified_count=1, upserted_id=inserted_id)
        return FakeUpdateResult(modified_count=0)


class FakePlanOrdersCollection(FakeCollection):
    def __init__(self, docs=None):
        super().__init__(docs)
        self.concurrent_existing_doc = None
        self.concurrent_open_order_doc = None

    async def insert_one(self, document):
        if self.concurrent_existing_doc is not None:
            self.docs.append(deepcopy(self.concurrent_existing_doc))
            self.concurrent_existing_doc = None
            raise DuplicateKeyError("duplicate key")
        if self.concurrent_open_order_doc is not None:
            self.docs.append(deepcopy(self.concurrent_open_order_doc))
            self.concurrent_open_order_doc = None
            raise DuplicateKeyError("duplicate key")
        return await super().insert_one(document)


class FakeDB:
    def __init__(self, *, provider_plans=None, billing_plans=None, plan_orders=None, credit_ledger=None, billing_webhook_events=None, billing_event_log=None):
        self.provider_plans = FakeCollection(provider_plans)
        self.billing_plans = FakeCollection(billing_plans)
        self.plan_orders = FakePlanOrdersCollection(plan_orders)
        self.credit_ledger = FakeCollection(credit_ledger)
        self.billing_webhook_events = FakeCollection(billing_webhook_events)
        self.billing_event_log = FakeCollection(billing_event_log)


class OperatorBillingOrderHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_order_recovers_idempotent_result_after_duplicate_key_race(self):
        existing_order = {
            "_id": ObjectId(),
            "operator_profile_id": "op-1",
            "client_request_id": "req-1",
            "order_status": "pending_payment",
            "order_code": "PORD-RACE-1",
            "created_at": datetime.now(timezone.utc),
        }
        fake_db = FakeDB(
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-1",
                    "operator_user_id": "user-1",
                    "plan_status": "active",
                    "credits_remaining": 0,
                }
            ],
            billing_plans=[{"code": "FREE", "name": "Free", "included_credits": 0}],
            plan_orders=[],
        )
        fake_db.plan_orders.concurrent_existing_doc = existing_order

        order, created = await create_operator_plan_order(
            fake_db,
            operator_profile_id="op-1",
            operator_user_id="user-1",
            organization_id="org-1",
            plan_doc={
                "code": "PRO",
                "name": "Pro",
                "description": "Paid plan",
                "monthly_price": 99,
                "currency": "INR",
                "included_credits": 100,
                "features": [],
            },
            payment_provider="razorpay",
            client_request_id="req-1",
        )

        self.assertFalse(created)
        self.assertEqual(order["order_code"], "PORD-RACE-1")

    async def test_create_order_raises_open_order_exists_when_race_creates_open_order(self):
        open_order = {
            "_id": ObjectId(),
            "operator_profile_id": "op-2",
            "client_request_id": "other-req",
            "order_status": "pending_payment",
            "order_code": "PORD-OPEN-1",
            "created_at": datetime.now(timezone.utc),
        }
        fake_db = FakeDB(
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-2",
                    "operator_user_id": "user-2",
                    "plan_status": "active",
                    "credits_remaining": 0,
                }
            ],
            billing_plans=[{"code": "FREE", "name": "Free", "included_credits": 0}],
            plan_orders=[],
        )
        fake_db.plan_orders.concurrent_open_order_doc = open_order

        with self.assertRaises(ValueError) as exc:
            await create_operator_plan_order(
                fake_db,
                operator_profile_id="op-2",
                operator_user_id="user-2",
                organization_id="org-2",
                plan_doc={
                    "code": "PRO",
                    "name": "Pro",
                    "description": "Paid plan",
                    "monthly_price": 99,
                    "currency": "INR",
                    "included_credits": 100,
                    "features": [],
                },
                payment_provider="razorpay",
                client_request_id="req-2",
            )

        self.assertEqual(str(exc.exception), "open_order_exists")

    async def test_cancel_order_returns_conflict_when_state_changes_during_update(self):
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-3",
                    "order_status": "pending_payment",
                    "payment_status": "not_started",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                }
            ]
        )

        async def conflict_update_one(query, update, upsert=False):
            _ = (query, update, upsert)
            return FakeUpdateResult(modified_count=0)

        fake_db.plan_orders.update_one = conflict_update_one

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with self.assertRaises(HTTPException) as exc:
                await cancel_operator_billing_order(
                    str(order_id),
                    access_context={
                        "operator_profile": {"_id": "op-3"},
                        "principal": {"_id": "user-3"},
                    },
                )

        self.assertEqual(exc.exception.status_code, 409)

    async def test_assign_plan_is_idempotent_for_same_source_order_id(self):
        source_order_id = str(ObjectId())
        fake_db = FakeDB(
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-4",
                    "operator_user_id": "user-4",
                    "plan_status": "active",
                    "plan_code": "FREE",
                    "plan_name": "Free",
                    "included_credits": 0,
                    "credits_remaining": 0,
                    "billing_cycle_start_at": datetime.now(timezone.utc),
                    "billing_cycle_end_at": datetime.now(timezone.utc),
                    "last_fulfilled_order_id": None,
                }
            ],
            credit_ledger=[],
        )

        plan_doc = {
            "code": "PRO",
            "name": "Pro",
            "description": "Paid plan",
            "monthly_price": 99,
            "currency": "INR",
            "included_credits": 100,
            "features": [],
        }

        first = await assign_plan_to_operator(
            fake_db,
            operator_profile_id="op-4",
            operator_user_id="user-4",
            plan_doc=plan_doc,
            actor_id="admin-1",
            notes="first completion",
            source_order_id=source_order_id,
            reset_credits=True,
        )
        second = await assign_plan_to_operator(
            fake_db,
            operator_profile_id="op-4",
            operator_user_id="user-4",
            plan_doc=plan_doc,
            actor_id="admin-1",
            notes="retry completion",
            source_order_id=source_order_id,
            reset_credits=True,
        )

        self.assertEqual(first.get("credits_remaining"), 100)
        self.assertEqual(second.get("credits_remaining"), 100)
        self.assertEqual(second.get("last_fulfilled_order_id"), source_order_id)
        self.assertEqual(len(fake_db.credit_ledger.docs), 1)
        self.assertEqual(fake_db.credit_ledger.docs[0]["credits_delta"], 100)

    async def test_complete_order_retry_with_stale_payload_does_not_double_grant_credits(self):
        order_id = ObjectId()
        initial_order = {
            "_id": order_id,
            "operator_profile_id": "op-5",
            "operator_user_id": "user-5",
            "order_code": "PORD-COMPLETE-1",
            "plan_code": "PRO",
            "plan_snapshot": {
                "code": "PRO",
                "name": "Pro",
                "description": "Paid plan",
                "monthly_price": 99,
                "currency": "INR",
                "included_credits": 50,
                "features": [],
            },
            "order_status": "pending_payment",
            "payment_status": "not_started",
            "fulfillment_status": "not_started",
            "status_history": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        fake_db = FakeDB(
            plan_orders=[initial_order],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-5",
                    "operator_user_id": "user-5",
                    "plan_status": "active",
                    "plan_code": "FREE",
                    "plan_name": "Free",
                    "included_credits": 0,
                    "credits_remaining": 0,
                    "billing_cycle_start_at": datetime.now(timezone.utc),
                    "billing_cycle_end_at": datetime.now(timezone.utc),
                    "last_fulfilled_order_id": None,
                }
            ],
            credit_ledger=[],
        )

        completed = await complete_operator_plan_order(
            fake_db,
            order=deepcopy(initial_order),
            actor_id="admin-5",
            payment_reference="manual-1",
            gateway_payment_id="pay-1",
            gateway_order_id="ord-1",
            settlement_notes="verified",
            gateway_metadata={"source": "test"},
        )

        retried = await complete_operator_plan_order(
            fake_db,
            order=deepcopy(initial_order),
            actor_id="admin-5",
            payment_reference="manual-1",
            gateway_payment_id="pay-1",
            gateway_order_id="ord-1",
            settlement_notes="verified",
            gateway_metadata={"source": "test"},
        )

        self.assertEqual(completed.get("order_status"), "completed")
        self.assertEqual(retried.get("order_status"), "completed")
        self.assertEqual(len(fake_db.credit_ledger.docs), 1)
        self.assertEqual(fake_db.credit_ledger.docs[0]["credits_delta"], 50)

    async def test_update_payment_state_promotes_pending_status_and_saves_references(self):
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-6",
                    "order_status": "pending_payment",
                    "payment_status": "not_started",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                }
            ]
        )

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            response = await update_operator_plan_order_payment_state(
                str(order_id),
                PlanOrderPaymentStateUpdateRequest(gateway_session_id="sess-1", gateway_order_id="ord-1"),
                access_context={
                    "operator_profile": {"_id": "op-6"},
                    "principal": {"_id": "user-6"},
                },
            )

        self.assertEqual(response["message"], "Plan order payment references updated")
        self.assertEqual(response["order"]["order_status"], "payment_pending")
        self.assertEqual(response["order"]["payment_status"], "pending")
        self.assertEqual(response["order"]["gateway_session_id"], "sess-1")

    async def test_update_payment_state_rejects_terminal_orders(self):
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-7",
                    "order_status": "completed",
                    "payment_status": "paid",
                    "fulfillment_status": "completed",
                    "status_history": [],
                }
            ]
        )

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with self.assertRaises(HTTPException) as exc:
                await update_operator_plan_order_payment_state(
                    str(order_id),
                    PlanOrderPaymentStateUpdateRequest(gateway_session_id="sess-2"),
                    access_context={
                        "operator_profile": {"_id": "op-7"},
                        "principal": {"_id": "user-7"},
                    },
                )

        self.assertEqual(exc.exception.status_code, 400)

    async def test_create_order_response_includes_checkout_scaffold_payload(self):
        fake_db = FakeDB(
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-8",
                    "operator_user_id": "user-8",
                    "plan_status": "active",
                    "credits_remaining": 0,
                }
            ],
            billing_plans=[
                {
                    "code": "PRO",
                    "name": "Pro",
                    "description": "Paid plan",
                    "monthly_price": 99,
                    "currency": "INR",
                    "included_credits": 100,
                    "features": [],
                    "is_active": True,
                },
                {"code": "FREE", "name": "Free", "included_credits": 0, "is_active": True},
            ],
            plan_orders=[],
        )

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            response = await create_operator_billing_order(
                OperatorPlanOrderCreateRequest(
                    plan_code="PRO",
                    payment_provider="razorpay",
                    client_request_id="req-8",
                ),
                access_context={
                    "operator_profile": {"_id": "op-8"},
                    "principal": {"_id": "user-8"},
                    "organization": {"_id": "org-8"},
                },
            )

        self.assertTrue(response["created"])
        self.assertEqual(response["gateway_status"], "not_configured")
        self.assertIn("checkout", response)
        self.assertEqual(response["checkout"]["gateway_status"], "not_configured")

    async def test_webhook_marks_order_payment_received_and_is_idempotent(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-9",
                    "order_code": "PORD-WEBHOOK-1",
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            billing_webhook_events=[],
        )

        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay-9",
                        "order_id": "gw-order-9",
                        "notes": {"order_code": "PORD-WEBHOOK-1"},
                    }
                }
            },
        }
        import json
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"test-secret", payload_bytes, hashlib.sha256).hexdigest()

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(True, "verified")):
                class FakeRequest:
                    async def body(self):
                        return payload_bytes

                first = await operator_billing_router_module.handle_operator_billing_webhook(
                    provider="razorpay",
                    request=FakeRequest(),
                    x_razorpay_signature=signature,
                    stripe_signature=None,
                    x_payu_signature=None,
                )
                second = await operator_billing_router_module.handle_operator_billing_webhook(
                    provider="razorpay",
                    request=FakeRequest(),
                    x_razorpay_signature=signature,
                    stripe_signature=None,
                    x_payu_signature=None,
                )

        self.assertTrue(first["ok"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(first["order_update_applied"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["duplicate"])
        updated_order = fake_db.plan_orders.docs[0]
        self.assertEqual(updated_order["order_status"], "payment_received")
        self.assertEqual(updated_order["payment_status"], "authorized")
        self.assertEqual(len(fake_db.billing_webhook_events.docs), 1)

    async def test_webhook_rejects_invalid_signature(self):
        fake_db = FakeDB()

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(False, "invalid_signature")):
                class FakeRequest:
                    async def body(self):
                        return b"{}"

                with self.assertRaises(HTTPException) as exc:
                    await operator_billing_router_module.handle_operator_billing_webhook(
                        provider="razorpay",
                        request=FakeRequest(),
                        x_razorpay_signature="bad",
                        stripe_signature=None,
                        x_payu_signature=None,
                    )

        self.assertEqual(exc.exception.status_code, 401)

    async def test_webhook_marks_order_failed_for_failure_event(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-10",
                    "order_code": "PORD-WEBHOOK-2",
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            billing_webhook_events=[],
        )

        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay-10",
                        "order_id": "gw-order-10",
                        "notes": {"order_code": "PORD-WEBHOOK-2"},
                    }
                }
            },
        }
        import json
        payload_bytes = json.dumps(payload).encode("utf-8")

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(True, "verified")):
                class FakeRequest:
                    async def body(self):
                        return payload_bytes

                response = await operator_billing_router_module.handle_operator_billing_webhook(
                    provider="razorpay",
                    request=FakeRequest(),
                    x_razorpay_signature="sig",
                    stripe_signature=None,
                    x_payu_signature=None,
                )

        self.assertTrue(response["ok"])
        self.assertTrue(response["order_update_applied"])
        updated_order = fake_db.plan_orders.docs[0]
        self.assertEqual(updated_order["order_status"], "failed")
        self.assertEqual(updated_order["payment_status"], "failed")

    async def test_webhook_marks_payment_refunded_for_completed_order(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-11",
                    "order_code": "PORD-WEBHOOK-3",
                    "order_status": "completed",
                    "payment_status": "paid",
                    "fulfillment_status": "completed",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            billing_webhook_events=[],
        )

        payload = {
            "event": "payment.refunded",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay-11",
                        "order_id": "gw-order-11",
                        "notes": {"order_code": "PORD-WEBHOOK-3"},
                    }
                }
            },
        }
        import json
        payload_bytes = json.dumps(payload).encode("utf-8")

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(True, "verified")):
                class FakeRequest:
                    async def body(self):
                        return payload_bytes

                response = await operator_billing_router_module.handle_operator_billing_webhook(
                    provider="razorpay",
                    request=FakeRequest(),
                    x_razorpay_signature="sig",
                    stripe_signature=None,
                    x_payu_signature=None,
                )

        self.assertTrue(response["ok"])
        self.assertTrue(response["order_update_applied"])
        self.assertIsNone(response.get("refund_compensation"))
        updated_order = fake_db.plan_orders.docs[0]
        self.assertEqual(updated_order["order_status"], "completed")
        self.assertEqual(updated_order["payment_status"], "refunded")

    async def test_webhook_refund_auto_compensates_when_mode_is_automatic(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-11b",
                    "operator_user_id": "user-11b",
                    "order_code": "PORD-WEBHOOK-3B",
                    "plan_snapshot": {
                        "code": "PRO",
                        "name": "Pro",
                        "included_credits": 15,
                    },
                    "order_status": "completed",
                    "payment_status": "paid",
                    "fulfillment_status": "completed",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-11b",
                    "operator_user_id": "user-11b",
                    "plan_status": "active",
                    "plan_code": "PRO",
                    "plan_name": "Pro",
                    "included_credits": 15,
                    "credits_remaining": 5,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                }
            ],
            credit_ledger=[],
            billing_webhook_events=[],
        )

        payload = {
            "event": "payment.refunded",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay-11b",
                        "order_id": "gw-order-11b",
                        "notes": {"order_code": "PORD-WEBHOOK-3B"},
                    }
                }
            },
        }
        import json
        payload_bytes = json.dumps(payload).encode("utf-8")

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(True, "verified")):
                with patch.object(operator_billing_router_module.settings, "billing_refund_compensation_mode", "automatic"):
                    class FakeRequest:
                        async def body(self):
                            return payload_bytes

                    response = await operator_billing_router_module.handle_operator_billing_webhook(
                        provider="razorpay",
                        request=FakeRequest(),
                        x_razorpay_signature="sig",
                        stripe_signature=None,
                        x_payu_signature=None,
                    )

        self.assertTrue(response["ok"])
        self.assertTrue(response["order_update_applied"])
        compensation = response.get("refund_compensation") or {}
        self.assertTrue(compensation.get("applied"))
        self.assertEqual(fake_db.provider_plans.docs[0]["credits_remaining"], 20)
        self.assertEqual(len(fake_db.credit_ledger.docs), 1)
        self.assertEqual(fake_db.credit_ledger.docs[0]["entry_type"], "refund")

    async def test_expire_stale_plan_orders_expires_only_unpaid_stale_orders(self):
        now = datetime.now(timezone.utc)
        stale_time = now.replace(year=now.year - 1)
        fresh_time = now.replace(year=now.year + 1)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "order_status": "pending_payment",
                    "payment_status": "not_started",
                    "fulfillment_status": "not_started",
                    "expires_at": stale_time,
                    "status_history": [],
                },
                {
                    "_id": ObjectId(),
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "expires_at": stale_time,
                    "status_history": [],
                },
                {
                    "_id": ObjectId(),
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "expires_at": fresh_time,
                    "status_history": [],
                },
            ]
        )

        result = await expire_stale_plan_orders(fake_db, now=now, limit=50)

        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["expired"], 2)
        statuses = [row["order_status"] for row in fake_db.plan_orders.docs]
        self.assertEqual(statuses.count("expired"), 2)
        self.assertEqual(statuses.count("payment_pending"), 1)

    async def test_admin_expire_stale_orders_endpoint_returns_counts(self):
        now = datetime.now(timezone.utc)
        stale_time = now.replace(year=now.year - 1)
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": ObjectId(),
                    "order_status": "pending_payment",
                    "payment_status": "not_started",
                    "fulfillment_status": "not_started",
                    "expires_at": stale_time,
                    "status_history": [],
                }
            ]
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await expire_stale_orders(limit=100, admin={"_id": "admin-1"})

        self.assertEqual(response["message"], "Stale plan-order expiry run completed")
        self.assertEqual(response["matched"], 1)
        self.assertEqual(response["expired"], 1)

    async def test_admin_list_webhook_events_filters_by_provider(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_webhook_events=[
                {"_id": ObjectId(), "provider": "razorpay", "event_id": "evt-1", "processed": True, "created_at": now},
                {"_id": ObjectId(), "provider": "stripe", "event_id": "evt-2", "processed": True, "created_at": now},
            ]
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await list_billing_webhook_events(provider="razorpay", limit=100, admin={"_id": "admin-1"})

        self.assertEqual(response["count"], 1)
        self.assertEqual(response["events"][0]["provider"], "razorpay")

    async def test_complete_plan_order_enriches_from_related_webhook_event(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-12",
                    "operator_user_id": "user-12",
                    "order_code": "PORD-WEBHOOK-SETTLE",
                    "plan_code": "PRO",
                    "plan_snapshot": {
                        "code": "PRO",
                        "name": "Pro",
                        "description": "Paid plan",
                        "monthly_price": 99,
                        "currency": "INR",
                        "included_credits": 30,
                        "features": [],
                    },
                    "order_status": "payment_received",
                    "payment_status": "authorized",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-12",
                    "operator_user_id": "user-12",
                    "plan_status": "active",
                    "plan_code": "FREE",
                    "plan_name": "Free",
                    "included_credits": 0,
                    "credits_remaining": 0,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                    "last_fulfilled_order_id": None,
                }
            ],
            credit_ledger=[],
            billing_webhook_events=[
                {
                    "_id": ObjectId(),
                    "provider": "razorpay",
                    "event_id": "evt-settle-1",
                    "idempotency_key": "idem-evt-1",
                    "event_type": "payment.captured",
                    "payment_reference": "pay-ref-12",
                    "gateway_payment_id": "pay-12",
                    "gateway_order_id": "gw-order-12",
                    "order_code": "PORD-WEBHOOK-SETTLE",
                    "processed": True,
                    "created_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await complete_plan_order(
                str(order_id),
                PlanOrderSettlementRequest(
                    settlement_notes="verified via webhook",
                    gateway_metadata={},
                ),
                admin={"_id": "admin-1"},
            )

        self.assertEqual(response["order"]["order_status"], "completed")
        self.assertEqual(response["order"]["payment_reference"], "pay-ref-12")
        self.assertEqual(response["order"]["gateway_payment_id"], "pay-12")
        self.assertEqual(response["order"]["gateway_order_id"], "gw-order-12")
        metadata = response["order"].get("gateway_metadata") or {}
        self.assertEqual(metadata.get("settlement_source"), "webhook")
        self.assertEqual(metadata.get("webhook_event_id"), "evt-settle-1")

    async def test_admin_get_webhook_event_by_idempotency_key(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_webhook_events=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "idem-lookup-1",
                    "provider": "razorpay",
                    "event_id": "evt-lookup-1",
                    "processed": True,
                    "created_at": now,
                }
            ]
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await get_billing_webhook_event("idem-lookup-1", admin={"_id": "admin-1"})

        self.assertEqual(response["event"]["idempotency_key"], "idem-lookup-1")
        self.assertEqual(response["event"]["provider"], "razorpay")

    async def test_webhook_success_then_admin_completion_uses_webhook_references(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-13",
                    "operator_user_id": "user-13",
                    "order_code": "PORD-WEBHOOK-HANDOFF",
                    "plan_code": "PRO",
                    "plan_snapshot": {
                        "code": "PRO",
                        "name": "Pro",
                        "description": "Paid plan",
                        "monthly_price": 99,
                        "currency": "INR",
                        "included_credits": 20,
                        "features": [],
                    },
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-13",
                    "operator_user_id": "user-13",
                    "plan_status": "active",
                    "plan_code": "FREE",
                    "plan_name": "Free",
                    "included_credits": 0,
                    "credits_remaining": 0,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                    "last_fulfilled_order_id": None,
                }
            ],
            billing_webhook_events=[],
            credit_ledger=[],
        )

        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay-13",
                        "order_id": "gw-order-13",
                        "notes": {"order_code": "PORD-WEBHOOK-HANDOFF"},
                    }
                }
            },
        }
        import json
        payload_bytes = json.dumps(payload).encode("utf-8")

        with patch.object(operator_billing_router_module, "get_database", AsyncMock(return_value=fake_db)):
            with patch.object(operator_billing_router_module, "verify_payment_webhook_signature", return_value=(True, "verified")):
                class FakeRequest:
                    async def body(self):
                        return payload_bytes

                webhook_response = await operator_billing_router_module.handle_operator_billing_webhook(
                    provider="razorpay",
                    request=FakeRequest(),
                    x_razorpay_signature="sig",
                    stripe_signature=None,
                    x_payu_signature=None,
                )

        self.assertTrue(webhook_response["order_update_applied"])

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            complete_response = await complete_plan_order(
                str(order_id),
                PlanOrderSettlementRequest(settlement_notes="auto from webhook", gateway_metadata={}),
                admin={"_id": "admin-1"},
            )

        self.assertEqual(complete_response["order"]["order_status"], "completed")
        self.assertEqual(complete_response["order"]["payment_reference"], "pay-13")
        self.assertEqual(complete_response["order"]["gateway_payment_id"], "pay-13")
        self.assertEqual(complete_response["order"]["gateway_order_id"], "gw-order-13")

    async def test_admin_reprocess_webhook_event_is_replay_safe(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        event_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-14",
                    "order_code": "PORD-REPLAY-1",
                    "order_status": "payment_pending",
                    "payment_status": "pending",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            billing_webhook_events=[
                {
                    "_id": event_id,
                    "idempotency_key": "idem-replay-1",
                    "provider": "razorpay",
                    "event_id": "evt-replay-1",
                    "event_type": "payment.captured",
                    "order_code": "PORD-REPLAY-1",
                    "payment_reference": "pay-14",
                    "gateway_payment_id": "pay-14",
                    "gateway_order_id": "gw-order-14",
                    "processed": True,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            first = await reprocess_billing_webhook_event("idem-replay-1", admin={"_id": "admin-1"})
            second = await reprocess_billing_webhook_event("idem-replay-1", admin={"_id": "admin-1"})

        self.assertTrue(first["order_found"])
        self.assertTrue(first["order_update_applied"])
        self.assertTrue(second["order_found"])
        self.assertFalse(second["order_update_applied"])
        order = fake_db.plan_orders.docs[0]
        self.assertEqual(order["order_status"], "payment_received")
        self.assertEqual(order["payment_status"], "authorized")
        event = fake_db.billing_webhook_events.docs[0]
        self.assertEqual(len(event.get("reprocess_history") or []), 2)

    async def test_admin_refund_compensation_endpoint_is_idempotent(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-15",
                    "order_code": "PORD-REFUND-1",
                    "plan_snapshot": {"included_credits": 40},
                    "order_status": "completed",
                    "payment_status": "refunded",
                    "fulfillment_status": "completed",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-15",
                    "operator_user_id": "user-15",
                    "plan_status": "active",
                    "plan_code": "PRO",
                    "plan_name": "Pro",
                    "included_credits": 40,
                    "credits_remaining": 10,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                }
            ],
            credit_ledger=[],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            first = await apply_refund_compensation(
                str(order_id),
                RefundCreditCompensationRequest(notes="manual goodwill"),
                admin={"_id": "admin-1"},
            )
            second = await apply_refund_compensation(
                str(order_id),
                RefundCreditCompensationRequest(notes="manual goodwill"),
                admin={"_id": "admin-1"},
            )

        self.assertEqual(first["message"], "Refund compensation processed")
        self.assertEqual(second["message"], "Refund compensation already applied")
        self.assertEqual(len(fake_db.credit_ledger.docs), 1)
        self.assertEqual(fake_db.credit_ledger.docs[0]["credits_delta"], 40)
        self.assertEqual(fake_db.credit_ledger.docs[0].get("idempotency_key"), f"refund_compensation:{order_id}")
        self.assertEqual(fake_db.provider_plans.docs[0]["credits_remaining"], 50)
        order = fake_db.plan_orders.docs[0]
        self.assertTrue(order.get("refund_compensation_applied"))
        self.assertEqual(order.get("refund_compensation_state"), "applied")

    async def test_admin_refund_compensation_requires_completed_refunded_order(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-16",
                    "order_code": "PORD-REFUND-2",
                    "plan_snapshot": {"included_credits": 20},
                    "order_status": "payment_received",
                    "payment_status": "authorized",
                    "fulfillment_status": "not_started",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-16",
                    "operator_user_id": "user-16",
                    "plan_status": "active",
                    "plan_code": "PRO",
                    "plan_name": "Pro",
                    "included_credits": 20,
                    "credits_remaining": 5,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                }
            ],
            credit_ledger=[],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            with self.assertRaises(HTTPException) as exc:
                await apply_refund_compensation(
                    str(order_id),
                    RefundCreditCompensationRequest(notes="invalid state"),
                    admin={"_id": "admin-1"},
                )

        self.assertEqual(exc.exception.status_code, 400)

    async def test_admin_refund_compensation_reports_in_progress_state(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-17",
                    "order_code": "PORD-REFUND-3",
                    "plan_snapshot": {"included_credits": 25},
                    "order_status": "completed",
                    "payment_status": "refunded",
                    "fulfillment_status": "completed",
                    "refund_compensation_state": "processing",
                    "status_history": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            provider_plans=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-17",
                    "operator_user_id": "user-17",
                    "plan_status": "active",
                    "plan_code": "PRO",
                    "plan_name": "Pro",
                    "included_credits": 25,
                    "credits_remaining": 8,
                    "billing_cycle_start_at": now,
                    "billing_cycle_end_at": now,
                }
            ],
            credit_ledger=[],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await apply_refund_compensation(
                str(order_id),
                RefundCreditCompensationRequest(notes="retry while processing"),
                admin={"_id": "admin-1"},
            )

        self.assertEqual(response["message"], "Refund compensation is currently in progress")
        self.assertEqual(response["result"].get("reason"), "compensation_in_progress")
        self.assertEqual(fake_db.provider_plans.docs[0]["credits_remaining"], 8)
        self.assertEqual(len(fake_db.credit_ledger.docs), 0)

    async def test_reconcile_credit_events_reports_missing_debit_issue(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_event_log=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "event-1",
                    "operator_profile_id": "op-18",
                    "is_billable": True,
                    "credits_charged": 3,
                    "created_at": now,
                }
            ],
            credit_ledger=[],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await reconcile_credit_events(days=30, limit=100, admin={"_id": "admin-1"})

        self.assertEqual(response["billable_events"], 1)
        self.assertEqual(response["issue_count"], 1)
        self.assertEqual(response["issues"][0]["type"], "missing_debit")

    async def test_reconcile_credit_events_reports_orphan_debit(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_event_log=[],
            credit_ledger=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-19",
                    "entry_type": "debit",
                    "credits_delta": -2,
                    "billing_event_idempotency_key": "event-missing",
                    "created_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await reconcile_credit_events(days=30, limit=100, admin={"_id": "admin-1"})

        self.assertEqual(response["issue_count"], 0)
        self.assertEqual(response["orphan_debit_count"], 1)

    async def test_repair_reconciliation_repairs_orphan_debit_with_existing_event(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_event_log=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "event-20",
                    "operator_profile_id": "op-20",
                    "is_billable": False,
                    "credits_charged": 0,
                    "created_at": now,
                    "metadata": {},
                }
            ],
            credit_ledger=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-20",
                    "entry_type": "debit",
                    "credits_delta": -3,
                    "billing_event_idempotency_key": "event-20",
                    "created_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await repair_reconciliation_credit_events(days=30, limit=100, max_repairs=10, admin={"_id": "admin-1"})

        self.assertEqual(response["repaired"], 1)
        self.assertEqual(response["before"]["orphan_debit_count"], 1)
        self.assertEqual(response["after"]["orphan_debit_count"], 0)
        event = fake_db.billing_event_log.docs[0]
        self.assertTrue(event["is_billable"])
        self.assertEqual(event["credits_charged"], 3)
        self.assertTrue((event.get("metadata") or {}).get("reconciliation_repaired"))

    async def test_repair_reconciliation_repairs_credit_mismatch(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_event_log=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "event-21",
                    "operator_profile_id": "op-21",
                    "is_billable": True,
                    "credits_charged": 5,
                    "created_at": now,
                    "metadata": {},
                }
            ],
            credit_ledger=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-21",
                    "entry_type": "debit",
                    "credits_delta": -2,
                    "billing_event_idempotency_key": "event-21",
                    "created_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await repair_reconciliation_credit_events(days=30, limit=100, max_repairs=10, admin={"_id": "admin-1"})

        self.assertEqual(response["repaired"], 1)
        self.assertEqual(response["before"]["issue_count"], 1)
        self.assertEqual(response["after"]["issue_count"], 0)
        event = fake_db.billing_event_log.docs[0]
        self.assertEqual(event["credits_charged"], 2)

    async def test_anomaly_counters_include_duplicate_attempts_failure_and_mismatch(self):
        now = datetime.now(timezone.utc)
        order_id = ObjectId()
        fake_db = FakeDB(
            plan_orders=[
                {
                    "_id": order_id,
                    "operator_profile_id": "op-22",
                    "order_code": "PORD-ANOM-1",
                    "plan_snapshot": {"included_credits": 10},
                    "order_status": "completed",
                    "payment_status": "refunded",
                    "fulfillment_status": "completed",
                    "refund_compensation_state": "failed",
                    "refund_compensation_duplicate_attempts": 2,
                    "updated_at": now,
                }
            ],
            billing_event_log=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "event-22",
                    "operator_profile_id": "op-22",
                    "is_billable": True,
                    "credits_charged": 3,
                    "created_at": now,
                }
            ],
            credit_ledger=[
                {
                    "_id": ObjectId(),
                    "operator_profile_id": "op-22",
                    "entry_type": "debit",
                    "credits_delta": -1,
                    "billing_event_idempotency_key": "event-22",
                    "created_at": now,
                }
            ],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await get_credit_reconciliation_anomalies(days=30, limit=100, admin={"_id": "admin-1"})

        anomalies = response["anomalies"]
        self.assertEqual(anomalies["duplicate_attempt_count"], 2)
        self.assertEqual(anomalies["compensation_failure_count"], 1)
        self.assertGreaterEqual(anomalies["mismatch_count"], 1)
        self.assertEqual(anomalies["mismatch_breakdown"]["credit_mismatch"], 1)

    async def test_export_reconciliation_issues_returns_csv(self):
        now = datetime.now(timezone.utc)
        fake_db = FakeDB(
            billing_event_log=[
                {
                    "_id": ObjectId(),
                    "idempotency_key": "event-23",
                    "operator_profile_id": "op-23",
                    "event_type": "intent_click",
                    "is_billable": True,
                    "credits_charged": 2,
                    "created_at": now,
                }
            ],
            credit_ledger=[],
        )

        with patch("backend.routers.admin_billing.get_database", AsyncMock(return_value=fake_db)):
            response = await export_credit_reconciliation_issues(days=30, limit=100, format="csv", admin={"_id": "admin-1"})

        content = response.body.decode("utf-8")
        self.assertIn("row_type,issue_type,operator_profile_id,event_idempotency_key", content)
        self.assertIn("issue,missing_debit,op-23,event-23", content)


if __name__ == "__main__":
    unittest.main()
