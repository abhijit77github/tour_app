import unittest
import time

from backend.utils.authorization import (
    RBAC_DENY_UNMAPPED_PERMISSION,
    has_permission,
    is_recent_auth_payload,
    required_permission_for_request,
)
from backend.utils.policy_registry import has_registry_rule_match, resolve_permission_from_registry


class PolicyRegistryTests(unittest.TestCase):
    def test_resolves_operator_quote_respond_dynamic_path(self):
        permission = resolve_permission_from_registry(
            principal_type="user",
            path="/quotes/abc123/respond",
            method="POST",
        )
        self.assertEqual(permission, "operator.quotes.respond")

    def test_resolves_admin_dashboard(self):
        permission = resolve_permission_from_registry(
            principal_type="admin",
            path="/admin/dashboard/stats",
            method="GET",
        )
        self.assertEqual(permission, "admin.dashboard.read")

    def test_resolves_authorization_report_endpoint(self):
        permission = resolve_permission_from_registry(
            principal_type="admin",
            path="/admin/audit/authorization-decisions",
            method="GET",
        )
        self.assertEqual(permission, "admin.audit.read")

    def test_resolves_operator_ticket_comment_path(self):
        permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operator/tickets/abc123/comments",
            method="POST",
        )
        self.assertEqual(permission, "operator.tickets.create")

    def test_resolves_admin_ticket_update_path(self):
        permission = resolve_permission_from_registry(
            principal_type="admin",
            path="/admin/tickets/abc123",
            method="PATCH",
        )
        self.assertEqual(permission, "admin.tickets.manage")

    def test_resolves_operator_billing_orders_by_method(self):
        read_permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operator/billing/orders",
            method="GET",
        )
        write_permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operator/billing/orders",
            method="POST",
        )
        self.assertEqual(read_permission, "operator.billing.read")
        self.assertEqual(write_permission, "operator.billing.manage")

    def test_resolves_operator_ticket_list_by_method(self):
        read_permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operator/tickets",
            method="GET",
        )
        write_permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operator/tickets",
            method="POST",
        )
        self.assertEqual(read_permission, "operator.tickets.read")
        self.assertEqual(write_permission, "operator.tickets.create")

    def test_resolves_public_operator_discovery_path_to_none(self):
        permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operators/search/location",
            method="GET",
        )
        self.assertIsNone(permission)

    def test_resolves_public_operator_profile_only_for_objectid(self):
        valid_permission = resolve_permission_from_registry(
            principal_type="user",
            path="/operators/507f1f77bcf86cd799439011",
            method="GET",
        )
        valid_match = has_registry_rule_match(
            principal_type="user",
            path="/operators/507f1f77bcf86cd799439011",
            method="GET",
        )
        invalid_match = has_registry_rule_match(
            principal_type="user",
            path="/operators/not-an-objectid",
            method="GET",
        )
        self.assertIsNone(valid_permission)
        self.assertTrue(valid_match)
        self.assertFalse(invalid_match)


class AuthorizationGuardTests(unittest.TestCase):
    def test_unmapped_admin_path_denied_in_strict_mode(self):
        permission = required_permission_for_request(
            principal_type="admin",
            path="/admin/new-control-plane-endpoint",
            method="GET",
        )
        self.assertEqual(permission, RBAC_DENY_UNMAPPED_PERMISSION)

    def test_unmapped_operator_surface_denied_in_strict_mode(self):
        permission = required_permission_for_request(
            principal_type="user",
            path="/operators/new-rbac-surface",
            method="GET",
        )
        self.assertEqual(permission, RBAC_DENY_UNMAPPED_PERMISSION)

    def test_explicit_public_operator_path_is_not_denied(self):
        permission = required_permission_for_request(
            principal_type="user",
            path="/operators/search/location",
            method="GET",
        )
        self.assertIsNone(permission)

    def test_public_operator_profile_objectid_is_not_denied(self):
        permission = required_permission_for_request(
            principal_type="user",
            path="/operators/507f1f77bcf86cd799439011",
            method="GET",
        )
        self.assertIsNone(permission)

    def test_sentinel_permission_always_denied(self):
        allowed = has_permission({"platform.super_admin"}, RBAC_DENY_UNMAPPED_PERMISSION)
        self.assertFalse(allowed)

    def test_recent_auth_payload_accepts_fresh_iat(self):
        payload = {"iat": int(time.time())}
        is_recent = is_recent_auth_payload(payload, max_age_minutes=15)
        self.assertTrue(is_recent)


if __name__ == "__main__":
    unittest.main()
