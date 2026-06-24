# Organization Access Control Plan

## Goal

Introduce a future-proof access-control model for:

- operator organizations with multiple users
- scoped permissions per user within the same organization
- admin-side scoped access without requiring separate infrastructure

This plan deliberately avoids separate databases or separate deployments. It adds an organizational boundary and a membership/permission model inside the current shared application and shared database.

## Current State

The current authorization model is simple and global:

- tourist/operator users authenticate from the shared `users` collection
- operators are effectively single-user because `operator_profiles` are owned by one `user_id`
- admin users authenticate from the separate `admins` collection
- admin authorization is mostly a global `role` check
- route handlers generally scope operator actions by `current_user["_id"]`

This is sufficient for a single-operator-account model, but it will not scale cleanly to:

- multiple staff members under one operator business
- section-level access such as billing-only, content-only, notifications-only
- admin-side role separation such as support, finance, compliance, marketing, and super admin
- future migration to tenant-aware isolation if enterprise requirements appear later

## Recommended Core Construct

Use **organization-based access control** now.

Treat an organization as the business/security boundary. A user belongs to one or more organizations through memberships. Roles and permissions are granted through memberships, not directly on the user record.

This gives you:

- many users under one operator business
- many admins under one internal admin organization or workspace
- future ability to split organizations into stronger tenant isolation later
- a consistent model for both operator-side and admin-side access

## Design Principles

1. Keep `user` as the identity.
2. Add `organization` as the security boundary.
3. Add `membership` as the source of access.
4. Resolve permissions from roles plus optional overrides.
5. Scope business data by `organization_id` wherever ownership matters.
6. Keep platform-super-admin authority separate from organization-scoped authority.
7. Make authorization checks service-driven and reusable, not route-specific copy/paste.

## Target Model

### 1. Shared Identity Model

Unify around one identity concept for all human users.

Two acceptable paths:

- preferred: gradually converge `admins` into a shared identity table/collection model with user category metadata
- pragmatic first step: keep `users` and `admins` as-is, but normalize authorization around memberships and org-scoped claims

Because the current code already has separate admin and user auth flows, the pragmatic first step is lower risk.

## New Collections

### `organizations`

Represents operator businesses and internal admin workspaces.

Suggested fields:

- `_id`
- `name`
- `slug`
- `organization_type`: `operator`, `internal_admin`, later optionally `partner`
- `status`: `active`, `suspended`, `archived`
- `settings`
- `created_at`
- `updated_at`

### `organization_memberships`

Represents which identity belongs to which organization and with what access.

Suggested fields:

- `_id`
- `organization_id`
- `principal_type`: `user`, `admin`
- `principal_id`
- `membership_status`: `invited`, `active`, `suspended`, `revoked`
- `role_keys`: array of role identifiers
- `permission_overrides`: optional allow/deny list
- `scope_constraints`: resource-level constraints
- `invited_by`
- `created_at`
- `updated_at`
- `last_accepted_at`

### `roles`

Stores reusable role definitions.

Suggested fields:

- `_id`
- `organization_type`
- `key`
- `name`
- `description`
- `permissions`: array of permission keys
- `is_system`
- `created_at`
- `updated_at`

### Optional `audit_access_events`

Tracks security-relevant access changes.

Suggested fields:

- `actor_principal_type`
- `actor_principal_id`
- `organization_id`
- `action`
- `target_principal_id`
- `target_resource_type`
- `target_resource_id`
- `before`
- `after`
- `created_at`

## Resource Ownership Model

Add `organization_id` to data owned by a business or internal admin workspace.

### Operator-side resources that should become organization-owned

- `operator_profiles`
- promotions and promotion events
- operator billing ledgers and packages
- itineraries authored by operator staff
- operator-side notifications or internal tasks
- quote handling records where operator ownership matters

### Admin-side resources that should become organization-owned or org-aware

- admin notifications and alert routing policies
- internal admin preferences
- future admin task assignments, audit queues, review queues

### Resources that remain global but are accessed through organization scope

- tourists
- global catalog/search data
- public operator discovery

For these, organization checks apply to actions, not necessarily raw ownership.

## Permission Model

Use explicit permission keys, not only coarse roles.

### Operator permission families

- `operator.profile.read`
- `operator.profile.update`
- `operator.serving_areas.manage`
- `operator.quotes.read`
- `operator.quotes.respond`
- `operator.itineraries.manage`
- `operator.promotions.manage`
- `operator.billing.read`
- `operator.billing.manage`
- `operator.team.manage`
- `operator.notifications.manage`
- `operator.analytics.read`

### Admin permission families

- `admin.dashboard.read`
- `admin.tourists.read`
- `admin.operators.read`
- `admin.operators.manage`
- `admin.quotes.read`
- `admin.quotes.manage`
- `admin.notifications.manage`
- `admin.billing.read`
- `admin.billing.manage`
- `admin.audit.read`
- `admin.reports.read`
- `admin.settings.manage`
- `admin.team.manage`

### Platform-only permissions

- `platform.organizations.manage`
- `platform.roles.manage`
- `platform.support.override`
- `platform.super_admin`

## Role Templates

### Operator org roles

- `operator_owner`
  - full access within one operator organization
- `operator_manager`
  - profile, quotes, itineraries, promotions, analytics
- `operator_sales`
  - quotes, promotions, limited customer comms
- `operator_content_editor`
  - profile, serving areas, itinerary content
- `operator_finance`
  - billing and package usage only
- `operator_support`
  - read-only operational visibility, notifications, limited actions

### Internal admin roles

- `platform_super_admin`
  - unrestricted
- `admin_operations`
  - operators, quotes, support workflows
- `admin_finance`
  - financial surfaces only
- `admin_marketing`
  - notifications, campaigns, promotions
- `admin_compliance`
  - audit, reviews, moderation, risk workflows
- `admin_readonly`
  - dashboards and reporting only

## Scope Constraints

Roles alone are not enough. Add optional constraints for finer control.

Examples:

- only assigned quote queues
- only specific serving states or countries
- only finance pages
- only read but not export
- only business hours notification operations

Suggested shape for `scope_constraints`:

```json
{
  "regions": ["goa", "karnataka"],
  "service_types": ["tour"],
  "quote_assignment_mode": "assigned_only",
  "billing_visibility": "read_only",
  "export_allowed": false
}
```

Keep this optional at first. Build the schema now, even if most checks initially rely only on permission keys.

## Authentication and Authorization Changes

## Token Claims

Extend access tokens to include enough context for fast authorization, but not the full permission matrix.

Suggested claims:

- `sub`
- `principal_type`: `user` or `admin`
- `active_organization_id`
- `membership_id`
- `role_keys`
- `session_version`

Do not put the full effective permission set into the token if you expect frequent role changes. Resolve permissions server-side using membership data and cache briefly if needed.

## Active Organization Selection

Support an active organization context.

This matters if one person can belong to more than one organization later.

Suggested behavior:

- login returns available organizations for that identity
- client stores active organization selection
- every protected request includes organization context via token claim and optionally header
- backend verifies the identity has an active membership for that organization

## Backend Authorization Layer

Add reusable helpers such as:

- `get_current_principal()`
- `get_active_membership()`
- `require_permission("operator.billing.read")`
- `require_any_permission([...])`
- `require_org_membership(organization_id)`

Avoid embedding raw role checks in route handlers. Route handlers should express intent, not access logic.

Bad:

```python
if current_user["user_type"] != "operator":
    raise HTTPException(...)
```

Better:

```python
membership = await require_permission(db, principal, "operator.profile.update")
```

## Data Migration Strategy

### Phase 0: Preparatory Schema

Add new collections and fields without changing behavior yet.

- create `organizations`
- create `organization_memberships`
- create `roles`
- add nullable `organization_id` to operator-owned collections

### Phase 1: Backfill Existing Operator Accounts

For every existing operator profile:

- create one operator organization
- attach the current operator user as `operator_owner`
- backfill `organization_id` into `operator_profiles`
- backfill `organization_id` into promotions, billing, itineraries, and other operator-owned records

### Phase 2: Backfill Existing Admin Accounts

Create one internal admin organization:

- create `internal_admin` organization
- attach current admins as memberships
- map current `super_admin` and `moderator` roles to new admin role templates

### Phase 3: Flip Authorization to Membership-Based Checks

- keep existing endpoints
- route access through new permission helpers
- keep legacy role checks only as temporary compatibility guards

### Phase 4: Enable Team Management UI

- invite user
- assign roles
- suspend/revoke member
- view audit history

## Indexing Plan

Add indexes early.

Recommended examples:

- `organizations.slug` unique
- `(organization_id, principal_type, principal_id)` unique on memberships
- `(organization_type, key)` unique on roles
- `(organization_id, created_at)` on org-owned activity tables
- `(organization_id, status)` where operational filtering is common
- `(organization_id, user_id)` or `(organization_id, operator_profile_id)` where ownership joins are frequent

## API Rollout Plan

## New endpoints

### Organization membership management

- `GET /orgs/me`
- `GET /orgs/{org_id}/members`
- `POST /orgs/{org_id}/members/invite`
- `PATCH /orgs/{org_id}/members/{membership_id}`
- `POST /orgs/{org_id}/members/{membership_id}/suspend`
- `POST /orgs/{org_id}/members/{membership_id}/reactivate`

### Role management

- `GET /roles?organization_type=operator`
- `GET /roles?organization_type=internal_admin`
- `POST /roles/custom`

### Session context

- `GET /auth/session-context`
- `POST /auth/active-organization`

## Existing endpoint refactors

Start with high-risk surfaces:

1. operator profile update
2. operator billing
3. promotions
4. quotes
5. itineraries
6. admin notifications
7. admin financial/audit/report surfaces

## Frontend Plan

### Operator side

Add a team-management section for operator owners/managers.

Capabilities:

- invite teammate
- assign role
- restrict billing access
- restrict content access
- suspend teammate
- audit recent changes

### Admin side

Add admin team management and visible permission groupings.

Capabilities:

- create internal admin membership
- assign admin role template
- optionally assign narrower scopes
- view effective access summary before saving

### UX rules

- hide routes user cannot access
- also enforce access server-side for every route
- show clear `forbidden` state, not silent redirects for every case

## Security Requirements

1. Every org-owned write must verify membership and permission.
2. Every org-owned read must include organization scoping by default.
3. Membership changes must be audited.
4. Role changes should invalidate or version old sessions.
5. Invitation flow should be time-bound and single-use.
6. Never trust frontend route hiding as authorization.
7. Avoid direct collection access from route handlers where tenant/org filters can be missed.

## Recommended Code Structure

Add a dedicated authorization module.

Suggested files:

- `backend/models/organization.py`
- `backend/models/access_control.py`
- `backend/utils/authorization.py`
- `backend/utils/organization_memberships.py`
- `backend/routers/org_memberships.py`

Keep policy logic centralized in utility/service modules so future extraction into a dedicated auth service remains practical.

## Suggested Implementation Phases

### Phase 1: Foundation

- add organizations, memberships, roles collections
- add org fields to operator-owned data
- seed system role templates
- add permission helpers

### Phase 2: Operator org access

- backfill one organization per operator business
- migrate operator routes from `user_id` ownership to membership + organization checks
- ship operator team management APIs

### Phase 3: Internal admin scoped access

- create internal admin organization
- migrate admin auth to membership-based permission checks
- ship admin team management APIs

### Phase 4: Resource-level constraints and audit hardening

- add optional scope constraints
- add export restrictions
- add access event audit trail
- add session invalidation/versioning

### Phase 5: Future tenant hardening

If enterprise needs grow later:

- add stricter tenant keys to all records
- isolate cache keys and background jobs per organization
- optionally split premium tenants by database or infrastructure later without rewriting the authorization model

## Migration Risk Notes

Main risks:

- hidden assumptions that one operator user equals one business
- old queries that filter only by `user_id`
- admin routes that assume global visibility and global write access
- missing backfill on historical billing/promotions/quote records

Mitigations:

- dual-write `organization_id` during transition
- add compatibility reads during migration window
- add cross-organization denial tests before flipping defaults
- migrate highest-risk routes first

## Recommendation Summary

For your stated need, the right long-term construct is:

- no separate infra now
- organization boundary for both operator businesses and internal admin workspace
- membership-based access
- role templates plus permission keys
- optional scope constraints for fine-grained access later

This gives you multiple users per operator organization, scoped admin access, and a clean path to stronger tenant isolation later without redesigning the access model again.