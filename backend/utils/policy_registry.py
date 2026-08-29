from __future__ import annotations

import re
from dataclasses import dataclass


READ_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class PolicyRule:
    principal_type: str
    method: str
    path_template: str
    permission: str | None

    def matches(self, *, principal_type: str, method: str, path: str) -> bool:
        if self.principal_type != principal_type:
            return False
        if self.method != "*" and self.method != method:
            return False
        return _path_template_matches(self.path_template, path)


def _path_template_matches(path_template: str, path: str) -> bool:
    segments = path_template.strip("/").split("/")
    regex_parts: list[str] = []
    for segment in segments:
        if segment.startswith("{") and segment.endswith("}"):
            token = segment[1:-1]
            _, _, constraint = token.partition(":")
            if constraint == "objectid":
                regex_parts.append(r"[0-9a-fA-F]{24}")
            else:
                regex_parts.append(r"[^/]+")
        else:
            regex_parts.append(re.escape(segment))

    regex = "/" + "/".join(regex_parts)
    return re.fullmatch(regex, path) is not None


POLICY_RULES: tuple[PolicyRule, ...] = (
    # Admin auth and team access
    PolicyRule("admin", "POST", "/admin/register", "platform.super_admin"),
    PolicyRule("admin", "POST", "/admin/login", None),
    PolicyRule("admin", "GET", "/admin/profile", None),
    PolicyRule("admin", "PUT", "/admin/profile", None),
    PolicyRule("admin", "POST", "/admin/change-password", None),
    PolicyRule("admin", "GET", "/admin/access/context", None),
    PolicyRule("admin", "GET", "/admin/team", "admin.team.manage"),
    PolicyRule("admin", "POST", "/admin/team", "admin.team.manage"),
    PolicyRule("admin", "*", "/admin/team/{membership_id}", "admin.team.manage"),
    # Admin platform sections
    PolicyRule("admin", "*", "/admin/dashboard/stats", "admin.dashboard.read"),
    PolicyRule("admin", "*", "/admin/dashboard/metrics", "admin.dashboard.read"),
    PolicyRule("admin", "*", "/admin/dashboard/response-times", "admin.dashboard.read"),
    PolicyRule("admin", "*", "/admin/tourists", "admin.tourists.read"),
    PolicyRule("admin", "*", "/admin/operators", "admin.operators.read"),
    PolicyRule("admin", "*", "/admin/operators/performance", "admin.operators.read"),
    PolicyRule("admin", "*", "/admin/operators/leaderboard", "admin.operators.read"),
    PolicyRule("admin", "*", "/admin/operators/{operator_id}/performance", "admin.operators.read"),
    PolicyRule("admin", "GET", "/admin/promotions/location", "admin.operators.manage"),
    PolicyRule("admin", "POST", "/admin/promotions/location", "admin.operators.manage"),
    PolicyRule("admin", "*", "/admin/promotions/location/{promotion_id}", "admin.operators.manage"),
    PolicyRule("admin", "GET", "/admin/users/{user_id}", "admin.tourists.read"),
    PolicyRule("admin", "POST", "/admin/users/{user_id}/suspend", "admin.operators.manage"),
    PolicyRule("admin", "POST", "/admin/users/{user_id}/activate", "admin.operators.manage"),
    PolicyRule("admin", "DELETE", "/admin/users/{user_id}", "admin.operators.manage"),
    PolicyRule("admin", "*", "/admin/quotes", "admin.quotes.read"),
    PolicyRule("admin", "*", "/admin/quotes/stats", "admin.quotes.read"),
    PolicyRule("admin", "*", "/admin/quotes/{quote_id}", "admin.quotes.read"),
    PolicyRule("admin", "*", "/admin/financial/overview", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/financial/transactions", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/financial/commissions", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/financial/payouts", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/financial/reports", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/audit/summary", "admin.audit.read"),
    PolicyRule("admin", "GET", "/admin/audit/authorization-decisions", "admin.audit.read"),
    PolicyRule("admin", "*", "/admin/reports/summary", "admin.reports.read"),
    PolicyRule("admin", "*", "/admin/reports", "admin.reports.manage"),
    PolicyRule("admin", "GET", "/admin/reports/{report_id}", "admin.reports.manage"),
    PolicyRule("admin", "DELETE", "/admin/reports/{report_id}", "admin.reports.manage"),
    PolicyRule("admin", "*", "/admin/reports/{report_id}/download", "admin.reports.read"),
    PolicyRule("admin", "*", "/admin/reports/schedules", "admin.reports.manage"),
    PolicyRule("admin", "*", "/admin/reports/schedules/{schedule_id}", "admin.reports.manage"),
    PolicyRule("admin", "*", "/admin/reports/dashboards", "admin.reports.manage"),
    PolicyRule("admin", "GET", "/admin/reports/dashboards/{dashboard_id}", "admin.reports.manage"),
    PolicyRule("admin", "PATCH", "/admin/reports/dashboards/{dashboard_id}", "admin.reports.manage"),
    PolicyRule("admin", "DELETE", "/admin/reports/dashboards/{dashboard_id}", "admin.reports.manage"),
    PolicyRule("admin", "*", "/admin/settings/summary", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/general", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/security", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/integration", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/api-keys", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/api-keys/{key_id}", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/webhooks", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/webhooks/{webhook_id}", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/settings/admin-users/{admin_id}", "platform.super_admin"),
    PolicyRule("admin", "*", "/admin/notifications/summary", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/alerts", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/alerts/{alert_id}/read", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/alerts/read-all", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/audience-preview", "admin.notifications.manage"),
    PolicyRule("admin", "GET", "/admin/notifications/templates", "admin.notifications.manage"),
    PolicyRule("admin", "POST", "/admin/notifications/templates", "admin.notifications.manage"),
    PolicyRule("admin", "PUT", "/admin/notifications/templates/{template_id}", "admin.notifications.manage"),
    PolicyRule("admin", "DELETE", "/admin/notifications/templates/{template_id}", "admin.notifications.manage"),
    PolicyRule("admin", "GET", "/admin/notifications/campaigns", "admin.notifications.manage"),
    PolicyRule("admin", "POST", "/admin/notifications/campaigns", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/campaigns/{campaign_id}", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/deliveries", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/worker-runs", "admin.notifications.manage"),
    PolicyRule("admin", "*", "/admin/notifications/worker-runs/trigger", "admin.notifications.manage"),
    PolicyRule("admin", "GET", "/admin/billing/plans", "admin.billing.manage"),
    PolicyRule("admin", "POST", "/admin/billing/plans", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/plans/{plan_id}", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/subscriptions", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/subscriptions/{operator_profile_id}/assign", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/plan-orders", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/plan-orders/{order_id}/complete", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/ledger", "admin.billing.read"),
    PolicyRule("admin", "GET", "/admin/billing/planner-pricing", "admin.billing.manage"),
    PolicyRule("admin", "POST", "/admin/billing/planner-pricing", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/planner-pricing/history", "admin.billing.read"),
    PolicyRule("admin", "GET", "/admin/billing/planner-quota", "admin.billing.manage"),
    PolicyRule("admin", "POST", "/admin/billing/planner-quota", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/planner-quota/history", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/planner-quota/ledger", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/planner-quota/reward-verifications", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/summary", "admin.billing.read"),
    PolicyRule("admin", "*", "/admin/billing/adjustments", "admin.billing.manage"),
    PolicyRule("admin", "*", "/admin/billing/events", "admin.billing.read"),
    PolicyRule("admin", "GET", "/admin/config/quote-limits", "admin.settings.manage"),
    PolicyRule("admin", "PUT", "/admin/config/quote-limits", "admin.settings.manage"),
    PolicyRule("admin", "*", "/admin/backups/capabilities", "admin.backups.manage"),
    PolicyRule("admin", "GET", "/admin/backups/jobs", "admin.backups.manage"),
    PolicyRule("admin", "POST", "/admin/backups/jobs", "admin.backups.manage"),
    PolicyRule("admin", "*", "/admin/backups/jobs/{job_id}", "admin.backups.manage"),
    PolicyRule("admin", "*", "/admin/backups/jobs/{job_id}/restore", "admin.backups.manage"),
    PolicyRule("admin", "*", "/admin/backups/jobs/{job_id}/download", "admin.backups.manage"),
    PolicyRule("admin", "*", "/admin/tickets", "admin.tickets.manage"),
    PolicyRule("admin", "GET", "/admin/tickets/{ticket_id}", "admin.tickets.manage"),
    PolicyRule("admin", "PATCH", "/admin/tickets/{ticket_id}", "admin.tickets.manage"),
    PolicyRule("admin", "*", "/admin/tickets/{ticket_id}/comments", "admin.tickets.manage"),
    # Operator access context and team
    PolicyRule("user", "GET", "/auth/me", None),
    PolicyRule("user", "GET", "/operators/search/location", None),
    PolicyRule("user", "GET", "/operators/serving-areas", None),
    PolicyRule("user", "GET", "/operators/{operator_id:objectid}", None),
    PolicyRule("user", "POST", "/operators/promotions/{promotion_id}/click", None),
    PolicyRule("user", "GET", "/operators/access/context", None),
    PolicyRule("user", "GET", "/operators/team", "operator.team.manage"),
    PolicyRule("user", "POST", "/operators/team", "operator.team.manage"),
    PolicyRule("user", "*", "/operators/team/{membership_id}", "operator.team.manage"),
    # Operator profile and templates
    PolicyRule("user", "POST", "/operators/profile", "operator.profile.update"),
    PolicyRule("user", "GET", "/operators/profile/me", "operator.profile.read"),
    PolicyRule("user", "PUT", "/operators/profile/me", "operator.profile.update"),
    PolicyRule("user", "*", "/operators/profile/serving-areas", "operator.profile.update"),
    PolicyRule("user", "*", "/operators/profile/serving-areas/{area_index}", "operator.profile.update"),
    PolicyRule("user", "GET", "/itineraries/operator/templates", "operator.itineraries.manage"),
    PolicyRule("user", "POST", "/itineraries/operator/templates", "operator.itineraries.manage"),
    PolicyRule("user", "*", "/itineraries/operator/templates/filter-options", "operator.itineraries.manage"),
    PolicyRule("user", "*", "/itineraries/operator/templates/{template_id}", "operator.itineraries.manage"),
    # Operator quote inbox/workflows
    PolicyRule("user", "GET", "/quotes/inbox", "operator.quotes.read"),
    PolicyRule("user", "GET", "/quotes/inbox/filter-options", "operator.quotes.read"),
    PolicyRule("user", "POST", "/quotes/{quote_id}/respond", "operator.quotes.respond"),
    # Billing / promotions / tickets
    PolicyRule("user", "*", "/operator/billing/plan", "operator.billing.read"),
    PolicyRule("user", "*", "/operator/billing/plans", "operator.billing.read"),
    PolicyRule("user", "GET", "/operator/billing/orders", "operator.billing.read"),
    PolicyRule("user", "POST", "/operator/billing/orders", "operator.billing.manage"),
    PolicyRule("user", "*", "/operator/billing/orders/{order_id}", "operator.billing.manage"),
    PolicyRule("user", "*", "/operator/billing/subscribe", "operator.billing.manage"),
    PolicyRule("user", "*", "/operator/billing/ledger", "operator.billing.read"),
    PolicyRule("user", "*", "/operator/billing/analytics", "operator.billing.read"),
    PolicyRule("user", "*", "/operator/promotions/packages", "operator.promotions.read"),
    PolicyRule("user", "*", "/operator/promotions/orders", "operator.promotions.manage"),
    PolicyRule("user", "*", "/operator/promotions/orders/{order_id}", "operator.promotions.manage"),
    PolicyRule("user", "*", "/operator/promotions/purchase", "operator.promotions.manage"),
    PolicyRule("user", "GET", "/operator/tickets", "operator.tickets.read"),
    PolicyRule("user", "POST", "/operator/tickets", "operator.tickets.create"),
    PolicyRule("user", "*", "/operator/tickets/{ticket_id}", "operator.tickets.read"),
    PolicyRule("user", "*", "/operator/tickets/{ticket_id}/comments", "operator.tickets.create"),
)


def resolve_permission_from_registry(*, principal_type: str, path: str, method: str) -> str | None:
    normalized_method = method.upper()
    for rule in POLICY_RULES:
        if rule.matches(principal_type=principal_type, method=normalized_method, path=path):
            permission = rule.permission
            if permission in {"operator.billing.read", "operator.billing.manage"}:
                return "operator.billing.read" if normalized_method in READ_METHODS else "operator.billing.manage"
            if permission in {"operator.promotions.read", "operator.promotions.manage"}:
                return "operator.promotions.read" if normalized_method in READ_METHODS else "operator.promotions.manage"
            if permission in {"operator.tickets.read", "operator.tickets.create"}:
                return "operator.tickets.read" if normalized_method in READ_METHODS else "operator.tickets.create"
            return permission
    return None


def has_registry_rule_match(*, principal_type: str, path: str, method: str) -> bool:
    normalized_method = method.upper()
    for rule in POLICY_RULES:
        if rule.matches(principal_type=principal_type, method=normalized_method, path=path):
            return True
    return False