# RBAC Endpoint Matrix and Phase-wise Implementation Plan

## 1) Objective

This document defines a practical RBAC rollout for the current backend API with four role planes:

- `tourist`
- `operator_user` (operator org member)
- `company_admin` (admin org member)
- `super_admin` (platform-level)

It provides:

- Endpoint-level access matrix aligned with current routers
- Permission namespace model (`tourist.*`, `operator.*`, `admin.*`, `platform.*`)
- Tenant/scope rules (`self`, `organization`, `global`)
- A phase-wise implementation checklist for execution tracking

Current execution status:

- Started: 2026-08-29
- Last updated: 2026-08-29
- Active phase: Completed (all planned phases closed for current rollout)

## 2) Role and Scope Model

### 2.1 Roles

- `tourist`: End user planning trips, requesting quotes, managing bookings, viewing personal notifications.
- `operator_user`: Operator-side user handling profile, quote inbox/respond, promotions, operator billing, operator tickets.
- `company_admin`: Admin-portal user for business operations inside an admin organization.
- `super_admin`: Highest privilege with cross-tenant/global controls.

### 2.2 Scope Constraints

- `self`: Only own user resources (`user_id == token.sub`)
- `organization`: Any resource in actor's organization (`organization_id == actor.org_id`)
- `global`: Platform-wide across organizations

### 2.3 Permission Key Pattern

Suggested canonical pattern:

- `resource.action`
- Examples:
  - `tourist.profile.read`
  - `tourist.booking.create`
  - `operator.quote.respond`
  - `admin.report.manage`
  - `platform.user.suspend`

## 3) Endpoint RBAC Matrix

Legend:

- Roles: `T` tourist, `O` operator_user, `A` company_admin, `S` super_admin
- Scope: `self`, `org`, `global`, `public`

---

## 3.1 Authentication (`/auth`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /auth/register | T,O | public | auth.register |
| POST | /auth/verify-registration-otp | T,O | public | auth.verify_otp |
| POST | /auth/resend-registration-otp | T,O | public | auth.resend_otp |
| POST | /auth/token | T,O | public | auth.login |
| POST | /auth/login | T,O | public | auth.login |
| GET | /auth/me | T,O | self | profile.read |
| POST | /auth/forgot-password | T,O | public | auth.forgot_password |
| POST | /auth/verify-otp | T,O | public | auth.verify_otp |
| POST | /auth/reset-password | T,O | public | auth.reset_password |

Notes:

- `A` and `S` admin login flows are handled under `/admin/login`.

---

## 3.2 Admin Authentication and Core Admin (`/admin`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /admin/register | S | global | platform.admin.create |
| POST | /admin/login | A,S | public | admin.auth.login |
| GET | /admin/profile | A,S | self | admin.profile.read |
| PUT | /admin/profile | A,S | self | admin.profile.update |
| POST | /admin/change-password | A,S | self | admin.profile.change_password |

### Dashboard and Monitoring

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/dashboard/stats | A,S | org/global | admin.dashboard.read |
| GET | /admin/dashboard/metrics | A,S | org/global | admin.dashboard.read |
| GET | /admin/dashboard/response-times | A,S | org/global | admin.dashboard.read |
| GET | /admin/audit/summary | A,S | org/global | admin.audit.read |

### User and Operator Oversight

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/tourists | A,S | org/global | admin.users.read |
| GET | /admin/operators | A,S | org/global | admin.operators.read |
| GET | /admin/users/{user_id} | A,S | org/global | admin.users.read |
| POST | /admin/users/{user_id}/suspend | S | global | platform.user.suspend |
| POST | /admin/users/{user_id}/activate | S | global | platform.user.activate |
| DELETE | /admin/users/{user_id} | S | global | platform.user.delete |

### Quote Oversight

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/quotes | A,S | org/global | admin.quotes.read |
| GET | /admin/quotes/stats | A,S | org/global | admin.quotes.read |
| GET | /admin/quotes/{quote_id} | A,S | org/global | admin.quotes.read |

### Operator Performance and Leaderboards

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/operators/performance | A,S | org/global | admin.operators.performance.read |
| GET | /admin/operators/leaderboard | A,S | org/global | admin.operators.performance.read |
| GET | /admin/operators/{operator_id}/performance | A,S | org/global | admin.operators.performance.read |

### Financial

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/financial/overview | A,S | org/global | admin.financial.read |
| GET | /admin/financial/transactions | A,S | org/global | admin.financial.read |
| GET | /admin/financial/commissions | A,S | org/global | admin.financial.read |
| GET | /admin/financial/payouts | A,S | org/global | admin.financial.read |
| GET | /admin/financial/reports | A,S | org/global | admin.financial.reports.read |

### Promotions (Location)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /admin/promotions/location | A,S | org/global | admin.promotions.manage |
| GET | /admin/promotions/location | A,S | org/global | admin.promotions.read |
| PATCH | /admin/promotions/location/{promotion_id} | A,S | org/global | admin.promotions.manage |
| DELETE | /admin/promotions/location/{promotion_id} | A,S | org/global | admin.promotions.manage |

### Reports and Dashboard Layouts

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/reports/summary | A,S | org/global | admin.reports.read |
| POST | /admin/reports | A,S | org/global | admin.reports.manage |
| GET | /admin/reports/{report_id} | A,S | org/global | admin.reports.read |
| DELETE | /admin/reports/{report_id} | A,S | org/global | admin.reports.manage |
| GET | /admin/reports/{report_id}/download | A,S | org/global | admin.reports.read |
| POST | /admin/reports/schedules | A,S | org/global | admin.reports.manage |
| PATCH | /admin/reports/schedules/{schedule_id} | A,S | org/global | admin.reports.manage |
| DELETE | /admin/reports/schedules/{schedule_id} | A,S | org/global | admin.reports.manage |
| GET | /admin/reports/dashboards/{dashboard_id} | A,S | org/global | admin.dashboard_layout.read |
| POST | /admin/reports/dashboards | A,S | org/global | admin.dashboard_layout.manage |
| PATCH | /admin/reports/dashboards/{dashboard_id} | A,S | org/global | admin.dashboard_layout.manage |
| DELETE | /admin/reports/dashboards/{dashboard_id} | A,S | org/global | admin.dashboard_layout.manage |

### Settings and Integrations

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/settings/summary | A,S | org/global | admin.settings.read |
| POST | /admin/settings/general | A,S | org/global | admin.settings.manage |
| POST | /admin/settings/security | A,S | org/global | admin.settings.manage |
| POST | /admin/settings/integration | A,S | org/global | admin.settings.manage |
| POST | /admin/settings/api-keys | A,S | org/global | admin.settings.manage |
| DELETE | /admin/settings/api-keys/{key_id} | A,S | org/global | admin.settings.manage |
| POST | /admin/settings/webhooks | A,S | org/global | admin.settings.manage |
| DELETE | /admin/settings/webhooks/{webhook_id} | A,S | org/global | admin.settings.manage |
| PATCH | /admin/settings/admin-users/{admin_id} | S | global | platform.admin.manage |

---

## 3.3 Access Control Team Management (`/operators/*`, `/admin/*` in access_control router)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /operators/access/context | O | org | operator.access_context.read |
| GET | /operators/team | O | org | operator.team.read |
| POST | /operators/team | O | org | operator.team.manage |
| PATCH | /operators/team/{membership_id} | O | org | operator.team.manage |
| GET | /admin/access/context | A,S | org/global | admin.access_context.read |
| GET | /admin/team | A,S | org/global | admin.team.read |
| POST | /admin/team | A,S | org/global | admin.team.manage |
| PATCH | /admin/team/{membership_id} | A,S | org/global | admin.team.manage |

---

## 3.4 Operators (`/operators`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /operators/profile | O | org | operator.profile.create |
| GET | /operators/profile/me | O | org | operator.profile.read |
| PUT | /operators/profile/me | O | org | operator.profile.update |
| POST | /operators/profile/serving-areas | O | org | operator.profile.update |
| PUT | /operators/profile/serving-areas/{area_index} | O | org | operator.profile.update |
| DELETE | /operators/profile/serving-areas/{area_index} | O | org | operator.profile.update |
| GET | /operators/serving-areas | T,O,A,S | self/org/global | None (public) |
| GET | /operators/{operator_id} | T,O,A,S | self/org/global | None (public) |
| GET | /operators/search/location | T,O,A,S | self/org/global | None (public) |
| POST | /operators/promotions/{promotion_id}/click | T | self | None (public) |

---

## 3.5 Quotes (`/quotes`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /quotes | T | self | tourist.quote.create |
| GET | /quotes/my | T | self | tourist.quote.read |
| GET | /quotes/inbox | O | org | operator.quote.inbox.read |
| GET | /quotes/inbox/filter-options | O | org | operator.quote.inbox.read |
| GET | /quotes/{quote_id} | T,O,A,S | self/org/global | quotes.read |
| POST | /quotes/{quote_id}/respond | O | org | operator.quote.respond |
| POST | /quotes/{quote_id}/close | T,O | self/org | quotes.close |
| POST | /quotes/{quote_id}/responses/{response_index}/save-itinerary | T | self | tourist.itinerary.save_from_quote |
| GET | /quotes/search/locations | T,O,A,S | self/org/global | quotes.search |
| GET | /quotes/destinations | T,O,A,S | self/org/global | quotes.search |

---

## 3.6 Bookings (`/bookings`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /bookings | T | self | tourist.booking.create |
| GET | /bookings/my-bookings | T | self | tourist.booking.read |
| GET | /bookings/{booking_id} | T,O,A,S | self/org/global | bookings.read |
| PUT | /bookings/{booking_id}/status | T,O,A,S | self/org/global | bookings.status.update |
| POST | /bookings/ratings | T | self | tourist.rating.create |
| GET | /bookings/ratings/operator/{operator_id} | T,O,A,S | self/org/global | ratings.read |
| GET | /bookings/ratings/booking/{booking_id} | T,O,A,S | self/org/global | ratings.read |
| PUT | /bookings/ratings/{rating_id} | T,A,S | self/org/global | ratings.update |

---

## 3.7 Chat (`/chat`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /chat/messages | T,O | self/org | chat.message.send |
| GET | /chat/messages/{other_user_id} | T,O | self/org | chat.message.read |
| GET | /chat/conversations | T,O | self/org | chat.conversation.read |
| GET | /chat/unread-count | T,O | self/org | chat.conversation.read |
| PUT | /chat/messages/{message_id}/read | T,O | self/org | chat.message.update |
| GET | /chat/retention-info | T,O,A,S | self/org/global | chat.retention.read |

---

## 3.8 Itineraries (`/itineraries`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /itineraries/search | T,O,A,S | self/org/global | itineraries.search |
| GET | /itineraries/operator/templates | O | org | operator.itinerary_template.read |
| GET | /itineraries/operator/templates/filter-options | O | org | operator.itinerary_template.read |
| POST | /itineraries/operator/templates | O | org | operator.itinerary_template.manage |
| PATCH | /itineraries/operator/templates/{template_id} | O | org | operator.itinerary_template.manage |
| DELETE | /itineraries/operator/templates/{template_id} | O | org | operator.itinerary_template.manage |
| GET | /itineraries/my | T | self | tourist.itinerary.read |
| POST | /itineraries/my | T | self | tourist.itinerary.create |
| POST | /itineraries/my/from-template/{template_id} | T | self | tourist.itinerary.create |
| PATCH | /itineraries/my/{itinerary_id} | T | self | tourist.itinerary.update |
| DELETE | /itineraries/my/{itinerary_id} | T | self | tourist.itinerary.delete |

---

## 3.9 Tour Planner (`/tour-planner`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /tour-planner/quota | T | self | tourist.planner.quota.read |
| POST | /tour-planner/quota/rewards/grant | T | self | tourist.planner.quota.grant |
| POST | /tour-planner/chat | T | self | tourist.planner.chat |
| POST | /tour-planner/confirm | T | self | tourist.planner.confirm |
| GET | /tour-planner/session/{session_id} | T | self | tourist.planner.session.read |
| GET | /tour-planner/session/{session_id}/itineraries | T | self | tourist.planner.session.read |

---

## 3.10 Recommendations (`/recommendations`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /recommendations/custom | T,O,A,S | self/org/global | recommendations.read |

---

## 3.11 Upload (`/upload`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| POST | /upload/profile-image | T,O,A,S | self/org/global | upload.profile_image |
| POST | /upload/location-images | O,A,S | org/global | upload.location_images |
| POST | /upload/ticket-attachments | T,O,A,S | self/org/global | upload.ticket_attachments |
| DELETE | /upload/image/{image_type}/{filename} | T,O,A,S | self/org/global | upload.delete |

---

## 3.12 Notifications (`/notifications`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /notifications/summary | T,O | self/org | notifications.read |
| GET | /notifications/inbox | T,O | self/org | notifications.read |
| POST | /notifications/inbox/{delivery_id}/read | T,O | self/org | notifications.update |
| POST | /notifications/inbox/read-all | T,O | self/org | notifications.update |
| GET | /notifications/preferences | T,O | self/org | notifications.preferences.read |
| PUT | /notifications/preferences | T,O | self/org | notifications.preferences.update |

---

## 3.13 Admin Notifications (`/admin/notifications`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/notifications/summary | A,S | org/global | admin.notifications.read |
| GET | /admin/notifications/alerts | A,S | org/global | admin.notifications.read |
| POST | /admin/notifications/alerts/{alert_id}/read | A,S | org/global | admin.notifications.manage |
| POST | /admin/notifications/alerts/read-all | A,S | org/global | admin.notifications.manage |
| POST | /admin/notifications/audience-preview | A,S | org/global | admin.notifications.manage |
| GET | /admin/notifications/templates | A,S | org/global | admin.notifications.read |
| POST | /admin/notifications/templates | A,S | org/global | admin.notifications.manage |
| PUT | /admin/notifications/templates/{template_id} | A,S | org/global | admin.notifications.manage |
| DELETE | /admin/notifications/templates/{template_id} | A,S | org/global | admin.notifications.manage |
| GET | /admin/notifications/campaigns | A,S | org/global | admin.notifications.read |
| GET | /admin/notifications/campaigns/{campaign_id} | A,S | org/global | admin.notifications.read |
| POST | /admin/notifications/campaigns | A,S | org/global | admin.notifications.manage |
| GET | /admin/notifications/deliveries | A,S | org/global | admin.notifications.read |
| GET | /admin/notifications/worker-runs | A,S | org/global | admin.notifications.read |
| POST | /admin/notifications/worker-runs/trigger | A,S | org/global | admin.notifications.manage |

---

## 3.14 Admin Billing (`/admin/billing`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/billing/plans | A,S | org/global | admin.billing.plans.read |
| POST | /admin/billing/plans | S | global | platform.billing.plans.manage |
| PATCH | /admin/billing/plans/{plan_id} | S | global | platform.billing.plans.manage |
| GET | /admin/billing/subscriptions | A,S | org/global | admin.billing.subscriptions.read |
| POST | /admin/billing/subscriptions/{operator_profile_id}/assign | A,S | org/global | admin.billing.subscriptions.manage |
| GET | /admin/billing/plan-orders | A,S | org/global | admin.billing.orders.read |
| POST | /admin/billing/plan-orders/{order_id}/complete | A,S | org/global | admin.billing.orders.manage |
| GET | /admin/billing/ledger | A,S | org/global | admin.billing.ledger.read |
| GET | /admin/billing/planner-pricing | A,S | org/global | admin.billing.pricing.read |
| POST | /admin/billing/planner-pricing | S | global | platform.billing.pricing.manage |
| GET | /admin/billing/planner-pricing/history | A,S | org/global | admin.billing.pricing.read |
| GET | /admin/billing/planner-quota | A,S | org/global | admin.billing.quota.read |
| POST | /admin/billing/planner-quota | A,S | org/global | admin.billing.quota.manage |
| GET | /admin/billing/planner-quota/history | A,S | org/global | admin.billing.quota.read |
| GET | /admin/billing/planner-quota/ledger | A,S | org/global | admin.billing.quota.read |
| GET | /admin/billing/planner-quota/reward-verifications | A,S | org/global | admin.billing.quota.read |
| GET | /admin/billing/summary | A,S | org/global | admin.billing.read |
| POST | /admin/billing/adjustments | S | global | platform.billing.adjustments.manage |
| GET | /admin/billing/events | A,S | org/global | admin.billing.events.read |

---

## 3.15 Operator Billing (`/operator/billing`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /operator/billing/plan | O | org | operator.billing.plan.read |
| GET | /operator/billing/plans | O | org | operator.billing.plans.read |
| GET | /operator/billing/orders | O | org | operator.billing.orders.read |
| POST | /operator/billing/orders | O | org | operator.billing.orders.create |
| DELETE | /operator/billing/orders/{order_id} | O | org | operator.billing.orders.cancel |
| POST | /operator/billing/subscribe | O | org | operator.billing.subscribe |
| GET | /operator/billing/ledger | O | org | operator.billing.ledger.read |
| GET | /operator/billing/analytics | O | org | operator.billing.analytics.read |

---

## 3.16 Operator Promotions (`/operator/promotions`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /operator/promotions/packages | O | org | operator.promotions.packages.read |
| GET | /operator/promotions/orders | O | org | operator.promotions.orders.read |
| POST | /operator/promotions/purchase | O | org | operator.promotions.purchase |
| DELETE | /operator/promotions/orders/{order_id} | O | org | operator.promotions.orders.cancel |

---

## 3.17 Admin Config (`/admin/config`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/config/quote-limits | A,S | org/global | admin.config.read |
| PUT | /admin/config/quote-limits | S | global | platform.config.quote_limits.manage |

---

## 3.18 Admin Backups (`/admin/backups`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /admin/backups/capabilities | S | global | platform.backups.read |
| GET | /admin/backups/jobs | S | global | platform.backups.read |
| GET | /admin/backups/jobs/{job_id} | S | global | platform.backups.read |
| POST | /admin/backups/jobs | S | global | platform.backups.manage |
| POST | /admin/backups/jobs/{job_id}/restore | S | global | platform.backups.restore |
| GET | /admin/backups/jobs/{job_id}/download | S | global | platform.backups.read |

---

## 3.19 Tickets (`/tickets`)

| Method | Endpoint | Roles | Scope | Permission |
|---|---|---|---|---|
| GET | /operator/tickets | O | org | operator.tickets.read |
| POST | /operator/tickets | O | org | operator.tickets.create |
| GET | /operator/tickets/{ticket_id} | O | org | operator.tickets.read |
| POST | /operator/tickets/{ticket_id}/comments | O | org | operator.tickets.create |
| GET | /admin/tickets | A,S | org/global | admin.tickets.manage |
| GET | /admin/tickets/{ticket_id} | A,S | org/global | admin.tickets.manage |
| POST | /admin/tickets/{ticket_id}/comments | A,S | org/global | admin.tickets.manage |
| PATCH | /admin/tickets/{ticket_id} | A,S | org/global | admin.tickets.manage |

---

## 4) Enforcement Rules (Must-Haves)

1. Deny-by-default:
- Any endpoint without explicit permission mapping must return `403`.

2. Scope-first checks:
- Permission pass alone is not enough; also enforce `self/org/global` ownership checks in query filters and document access.

3. Super-admin boundary:
- `S` can bypass org boundaries only for explicit `platform.*` permissions.

4. Sensitive actions hardening:
- Require fresh auth/MFA for critical operations:
  - user suspension/deletion
  - billing plan mutations
  - backup restore
  - admin-user role elevation

5. Immutable audit trail:
- Log actor, role, permission, scope decision, target resource id, outcome.

## 5) Phase-wise Implementation Plan

## Phase 0: Baseline and Freeze

Status: `DONE`

Checklist:

- [x] Confirm canonical role names in token claims (`tourist`, `operator_user`, `company_admin`, `super_admin`)
- [x] Freeze permission naming convention
- [x] Freeze endpoint-to-permission mapping (this document)
- [x] Identify sensitive endpoints requiring step-up auth

Acceptance Criteria:

- Approved RBAC spec reviewed by backend + frontend owners.

## Phase 1: Claims, Context, and Permission Registry

Status: `DONE`

Checklist:

- [x] Add role + org claims in auth/admin JWTs
- [x] Create centralized permission registry (single source of truth)
- [x] Add role templates for `operator_user`, `company_admin`, `super_admin`
- [x] Normalize access context builders for user/admin principals
- [x] Eager operator owner provisioning during onboarding verification

Acceptance Criteria:

- All authenticated requests expose stable principal context with role + organization metadata.

## Phase 2: Route-level Guard Enforcement

Status: `DONE`

Checklist:

- [x] Add explicit required-permission mapping for each router endpoint (registry-only)
- [x] Replace ad-hoc checks with shared dependency guard utilities
- [x] Enforce deny-by-default for unmapped protected routes (strict, always-on)
- [x] Add consistent `403` error payload format

Acceptance Criteria:

- Every protected endpoint enforces a named permission.

## Phase 3: Scope and Tenant Isolation Hardening

Status: `DONE`

Checklist:

- [x] Apply `self/org/global` constraints to read queries
- [x] Apply same constraints to write/update/delete operations
- [x] Add anti-IDOR checks for all `{id}` path parameters
- [x] Add negative tests proving cross-tenant denial

Acceptance Criteria:

- Cross-tenant data access is blocked by query-level and object-level checks.

## Phase 4: Sensitive Operations and Audit Controls

Status: `DONE`

Checklist:

- [x] Add step-up auth requirement for high-risk actions (feature-flagged)
- [x] Ensure immutable audit events for all admin/platform mutations
- [x] Add alerting rules for abusive failed attempts
- [x] Add break-glass policy for emergency super-admin actions

Acceptance Criteria:

- Sensitive actions require extra trust signal and are fully auditable.

## Phase 5: Test Suite, Rollout, and Observability

Status: `DONE`

Checklist:

- [x] Add permission matrix tests (allow + deny cases)
- [x] Add scope/tenant integration tests
- [x] Add production metrics (`403 rate`, denied-by-permission, denied-by-scope)
- [x] Canary rollout and staged enablement via feature flag
- [x] Post-rollout audit and documentation update

Acceptance Criteria:

- RBAC enforcement is test-backed, observable, and safely rolled out.

## 6) Progress Tracker Table

| Phase | Owner | Start Date | Target Date | Status | % Complete | Notes |
|---|---|---|---|---|---:|---|
| Phase 0 Baseline | Backend | 2026-08-29 | 2026-08-29 | DONE | 100 | Matrix, naming, and sensitive action list frozen |
| Phase 1 Claims/Registry | Backend | 2026-08-29 | 2026-09-02 | DONE | 100 | JWT claims live and eager operator-owner bootstrap completed |
| Phase 2 Guards | Backend | 2026-08-29 | 2026-09-05 | DONE | 100 | Registry-only resolver, expanded mappings, and strict deny guard implemented |
| Phase 3 Scope Isolation | Backend | 2026-08-29 | 2026-09-06 | DONE | 100 | Org-bound access control and anti-IDOR negative coverage added |
| Phase 4 Sensitive Controls | Backend | 2026-08-29 | 2026-09-06 | DONE | 100 | Step-up control path and authorization decision audit logging added |
| Phase 5 Rollout/Observability | Backend | 2026-08-29 | 2026-09-06 | DONE | 100 | RBAC tests added, regression suite passed, and rollout flags documented |

## 6.1 Progress Log

| Date | Phase | Update |
|---|---|---|
| 2026-08-29 | Phase 0 | Completed baseline freeze: canonical roles, permission naming, and endpoint matrix documented. |
| 2026-08-29 | Phase 1 | Implemented eager operator onboarding provisioning so verified operator gets owner membership immediately. |
| 2026-08-29 | Phase 2 | Added centralized policy registry and wired resolver for explicit route-permission enforcement. |
| 2026-08-29 | Phase 1 | Added JWT role and organization claims for user and admin login token issuance. |
| 2026-08-29 | Phase 2 | Expanded registry for admin and operator control-plane routes and enforced unmapped protected-route sentinel denial in strict mode. |
| 2026-08-29 | Phase 4 | Added feature-flagged step-up enforcement path for sensitive permissions and authorization decision audit events. |
| 2026-08-29 | Phase 5 | Added RBAC guard tests and ran RBAC + access-control regression suite successfully. |
| 2026-08-29 | Phase 3 | Added cross-organization negative test coverage for membership update paths (anti-IDOR). |

## 7) Implementation Notes for Current Codebase

- Existing helpers already present in codebase (`required_permission_for_request`, `has_permission`, membership context resolvers) should become the only enforcement path.
- Avoid embedding permission strings directly in business logic; keep them in a central policy registry and reference constants.
- For mixed endpoints (for example quote details visible to both tourists and operators), validate both permission and ownership/scope.
- Keep admin and user auth planes separate, but normalize authorization decision format to reduce drift.

## 8) Rollout Switches

Use these runtime flags to stage rollout safely:

- `RBAC_STEP_UP_REQUIRED=false` (set `true` to enforce recent-auth for sensitive permissions)
- `RBAC_STEP_UP_MAX_AGE_MINUTES=15`
- `RBAC_AUDIT_DECISIONS=true`

## 9) Authorization Observability

- API endpoint: `GET /admin/audit/authorization-decisions`
- Permission: `admin.audit.read`
- Query filters: `hours`, `limit`, `principal_type`, `decision`, `permission`, `path_contains`
- Response highlights: decision totals, denial rate, top denied permissions/routes, principal breakdown, recent authorization events.
