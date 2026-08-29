import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from backend.utils.audit_events import build_authorization_decision_report


class FakeAuditCursor:
    def __init__(self, docs):
        self.docs = [deepcopy(doc) for doc in docs]

    def sort(self, field, direction):
        reverse = direction == -1
        self.docs.sort(key=lambda doc: doc.get(field), reverse=reverse)
        return self

    async def to_list(self, length=0):
        if length and length > 0:
            return [deepcopy(doc) for doc in self.docs[:length]]
        return [deepcopy(doc) for doc in self.docs]


class FakeAuditCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in (docs or [])]

    @staticmethod
    def _nested_value(document, path):
        current = document
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _match_value(self, doc_value, expected):
        if isinstance(expected, dict):
            if "$gte" in expected:
                return doc_value is not None and doc_value >= expected["$gte"]
            if "$in" in expected:
                return doc_value in expected["$in"]
            return False
        return doc_value == expected

    def _matches(self, doc, query):
        for key, expected in query.items():
            value = self._nested_value(doc, key)
            if not self._match_value(value, expected):
                return False
        return True

    def find(self, query):
        matched = [doc for doc in self.docs if self._matches(doc, query)]
        return FakeAuditCursor(matched)


class FakeDB:
    def __init__(self, audit_docs):
        self.audit_events = FakeAuditCollection(audit_docs)

    def __getitem__(self, item):
        if item == "audit_events":
            return self.audit_events
        raise KeyError(item)


class AuthorizationReportingTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorization_report_summary_and_top_denials(self):
        now = datetime.now(timezone.utc)
        docs = [
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(minutes=5),
                "description": "deny billing write",
                "metadata": {
                    "principal_type": "user",
                    "principal_id": "u-1",
                    "permission": "operator.billing.manage",
                    "path": "/operator/billing/orders",
                    "method": "POST",
                    "decision": "denied",
                },
            },
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(minutes=3),
                "description": "allow billing read",
                "metadata": {
                    "principal_type": "user",
                    "principal_id": "u-2",
                    "permission": "operator.billing.read",
                    "path": "/operator/billing/orders",
                    "method": "GET",
                    "decision": "allowed",
                },
            },
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(minutes=2),
                "description": "deny billing write repeat",
                "metadata": {
                    "principal_type": "user",
                    "principal_id": "u-3",
                    "permission": "operator.billing.manage",
                    "path": "/operator/billing/orders",
                    "method": "POST",
                    "decision": "denied",
                },
            },
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(hours=48),
                "description": "outside window",
                "metadata": {
                    "principal_type": "admin",
                    "principal_id": "a-1",
                    "permission": "admin.audit.read",
                    "path": "/admin/audit/summary",
                    "method": "GET",
                    "decision": "allowed",
                },
            },
        ]
        report = await build_authorization_decision_report(FakeDB(docs), hours=24, limit=10)

        self.assertEqual(report["summary"]["total"], 3)
        self.assertEqual(report["summary"]["allowed"], 1)
        self.assertEqual(report["summary"]["denied"], 2)
        self.assertEqual(report["summary"]["denialRate"], 66.67)

        self.assertEqual(report["topDeniedPermissions"][0]["permission"], "operator.billing.manage")
        self.assertEqual(report["topDeniedPermissions"][0]["count"], 2)
        self.assertEqual(report["topDeniedRoutes"][0]["route"], "POST /operator/billing/orders")
        self.assertEqual(report["topDeniedRoutes"][0]["count"], 2)
        self.assertEqual(len(report["events"]), 3)

    async def test_authorization_report_supports_filters(self):
        now = datetime.now(timezone.utc)
        docs = [
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(minutes=1),
                "description": "user deny",
                "metadata": {
                    "principal_type": "user",
                    "principal_id": "u-1",
                    "permission": "operator.team.manage",
                    "path": "/operators/team",
                    "method": "POST",
                    "decision": "denied",
                },
            },
            {
                "_id": ObjectId(),
                "category": "security",
                "event_type": "authorization_decision",
                "timestamp": now - timedelta(minutes=1),
                "description": "admin deny",
                "metadata": {
                    "principal_type": "admin",
                    "principal_id": "a-1",
                    "permission": "admin.team.manage",
                    "path": "/admin/team",
                    "method": "POST",
                    "decision": "denied",
                },
            },
        ]

        report = await build_authorization_decision_report(
            FakeDB(docs),
            hours=24,
            principal_type="user",
            decision="denied",
            path_contains="operators/team",
        )

        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["summary"]["denied"], 1)
        self.assertEqual(report["filters"]["principal_type"], "user")
        self.assertEqual(report["filters"]["decision"], "denied")
        self.assertEqual(report["events"][0]["path"], "/operators/team")


if __name__ == "__main__":
    unittest.main()
