# Notification System Implementation Guide

## Purpose

This document defines the current production-ready notification implementation inside the Tour App monolith and the extraction seam that keeps it portable to a standalone microservice later.

The system is no longer UI-only. Templates, campaigns, scheduled execution, admin alerts, delivery attempts, user preferences, and the in-app inbox are all backed by the backend notification domain.

## Goals

- Persist admin-created notification templates and campaigns.
- Support immediate send and scheduled send records.
- Provide recipient audience preview before campaign creation.
- Keep the domain isolated behind a small router and service layer.
- Store enough campaign metadata to support queue workers and channel adapters later.
- Avoid coupling the admin UI to Mongo collection details.

## Current Non-Goals

- Real email, SMS, push, or WhatsApp provider delivery.
- External queue infrastructure or event bus integration.
- Automatic retry backoff and dead-letter reprocessing.
- Separate notification microservice deployment.

## Current Architecture

The notification domain stays inside the monolith, but it is already split across stable boundaries that can be extracted later with minimal contract churn.

### Boundary Rules

- FastAPI router handles auth, request validation, and HTTP serialization only.
- Notification service functions in `backend/utils/notifications.py` contain domain rules, persistence rules, and read models.
- Worker and adapter execution lives in `backend/utils/notification_delivery.py` behind a channel adapter contract.
- Notification schemas live in `backend/models/notification.py`.
- Admin APIs live in `backend/routers/admin_notifications.py`.
- End-user inbox and preference APIs live in `backend/routers/user_notifications.py`.
- UI only talks to stable REST contracts.
- No other domain should write directly to notification collections.

### Runtime Components

- Admin compose flow creates templates and campaigns.
- Immediate campaigns are processed synchronously through the same delivery path used by the worker.
- Scheduled campaigns are claimed by the background worker started in `backend/main.py`.
- Delivery adapters create per-user delivery rows and attempt logs.
- Admin alert rows capture operational visibility for failed or suspicious execution paths.
- End-user APIs expose inbox, unread summary, and preference management without changing the admin compose contract.

### Current Data Flow

#### Admin Compose To Inbox

1. Admin submits a campaign through `POST /admin/notifications/campaigns`.
2. Router validates auth and request shape.
3. Notification service normalizes recipient filters and stores the campaign.
4. If `send_now = true`, the service hands the campaign to the execution layer immediately.
5. The execution layer resolves matching users, loads preferences, applies suppression rules, and calls the configured adapter.
6. The in-app adapter writes `notification_deliveries` rows.
7. Execution writes `notification_delivery_attempts`, refreshes campaign stats, and records operational alerts when needed.
8. Users retrieve unread counts and inbox items through `/notifications/summary` and `/notifications/inbox`.

#### Scheduled Execution

1. Campaign is stored with `status = scheduled` and a future `scheduled_for` timestamp.
2. Startup in `backend/main.py` creates a background polling task.
3. The worker claims due campaigns by moving them to `processing` with a worker lock.
4. Claimed campaigns are processed through the same adapter flow as immediate sends.
5. Each worker run is written to `notification_worker_runs` for admin visibility.

#### Admin Operational Visibility

1. Admin summary reads campaign totals, unread admin alerts, and latest worker run.
2. Admin alerts page reads `admin_alerts`, recent delivery attempts, and worker-run history.
3. Admin top-bar badge polls the summary endpoint so unread alerts are live, not static.

### Extraction Path

When moving to a microservice later:

1. Keep the REST response shapes stable.
2. Replace direct Mongo calls inside `backend/utils/notifications.py` with RPC or HTTP client calls.
3. Keep collection-backed IDs as opaque strings now so caller code never depends on Mongo `ObjectId` internals.
4. Move scheduled execution into a worker in the new service without changing admin compose/history/template flows.

## Data Model

### `notification_templates`

Stores reusable admin-authored message templates.

Fields:

- `_id`
- `name`
- `category`
- `subject`
- `message`
- `channels`: array, phase 1 defaults to `in_app`
- `is_active`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

### `notification_campaigns`

Stores outbound campaign orchestration records.

Fields:

- `_id`
- `type`: `notification`, `announcement`, `alert`
- `subject`
- `message`
- `channel`: phase 1 uses `in_app`
- `recipient_type`: `tourists`, `operators`, `all`
- `recipient_filter`
- `recipient_count`
- `status`: `draft`, `scheduled`, `processing`, `sent`, `failed`, `cancelled`
- `scheduled_for`
- `sent_at`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`
- `delivery_stats`
- `worker_lock_id`
- `worker_locked_at`
- `last_worker_run_at`
- `failure_reason`
- `metadata`

### `notification_audit_log`

Stores audit rows for template and campaign lifecycle operations.

Fields:

- `_id`
- `entity_type`: `template`, `campaign`
- `entity_id`
- `action`: `created`, `updated`, `deleted`, `sent`, `scheduled`
- `actor_id`
- `actor_name`
- `created_at`
- `metadata`

### `notification_deliveries`

Stores per-user in-app delivery rows.

Fields:

- `_id`
- `campaign_id`
- `user_id`
- `subject`
- `message`
- `type`
- `channel`
- `status`: `delivered`, `read`, `suppressed`, `failed`
- `created_at`
- `delivered_at`
- `read_at`
- `suppression_reason`
- `metadata`

### `notification_delivery_attempts`

Stores execution-attempt telemetry for admin operations visibility.

Fields:

- `_id`
- `campaign_id`
- `user_id`
- `channel`
- `adapter`
- `status`
- `delivery_id`
- `failure_reason`
- `metadata`
- `created_at`

### `notification_preferences`

Stores end-user inbox and suppression preferences.

Fields:

- `_id`
- `user_id`
- `preferences.in_app_enabled`
- `preferences.marketing_enabled`
- `preferences.announcements_enabled`
- `preferences.alerts_enabled`
- `preferences.quiet_hours_enabled`
- `preferences.quiet_hours_start`
- `preferences.quiet_hours_end`
- `preferences.timezone`
- `created_at`
- `updated_at`

### `notification_worker_runs`

Stores one row per worker polling cycle that claims or attempts campaigns.

Fields:

- `_id`
- `worker_id`
- `started_at`
- `finished_at`
- `claimed_campaign_count`
- `processed_campaign_count`
- `status`
- `metadata`

### `admin_alerts`

Stores operator-facing alert feed rows for execution failures and abnormal conditions.

Fields:

- `_id`
- `title`
- `message`
- `severity`: `info`, `warning`, `error`
- `category`
- `read`
- `read_at`
- `source_reference_type`
- `source_reference_id`
- `metadata`
- `created_at`

## REST Contract

### Admin Templates

- `GET /admin/notifications/templates`
- `POST /admin/notifications/templates`
- `PUT /admin/notifications/templates/{template_id}`
- `DELETE /admin/notifications/templates/{template_id}`

### Admin Campaigns

- `GET /admin/notifications/campaigns`
- `POST /admin/notifications/campaigns`
- `GET /admin/notifications/campaigns/{campaign_id}`

### Admin Operations

- `GET /admin/notifications/summary`
- `GET /admin/notifications/alerts`
- `POST /admin/notifications/alerts/{alert_id}/read`
- `POST /admin/notifications/alerts/read-all`
- `GET /admin/notifications/deliveries`
- `GET /admin/notifications/worker-runs`
- `POST /admin/notifications/worker-runs/trigger`

### User Inbox And Preferences

- `GET /notifications/summary`
- `GET /notifications/inbox`
- `POST /notifications/inbox/{delivery_id}/read`
- `POST /notifications/inbox/read-all`
- `GET /notifications/preferences`
- `PUT /notifications/preferences`

### Audience Preview

- `POST /admin/notifications/audience-preview`

Returns projected audience count and recipient-type breakdown using current user collections.

## Audience Rules In Phase 1

- `tourists`: users with `user_type = tourist`
- `operators`: users with `user_type = operator`
- `all`: both groups
- `active_only`: excludes `is_active = False`
- `last_active_days`: filters by `last_login`, `updated_at`, or `created_at`

## Campaign Lifecycle

### Immediate Send

1. Admin previews audience.
2. Admin submits campaign.
3. Service resolves recipient count.
4. Campaign is written with `status = processing` and then executed through the shared delivery path.
5. The execution path creates per-user delivery rows, attempt logs, and refreshes aggregate delivery stats.
6. Campaign finishes as `sent` or `failed`.

### Scheduled Send

1. Admin selects a future date and time.
2. Service validates UTC timestamp is in the future.
3. Campaign is written with `status = scheduled`.
4. Background worker claims due records and executes them without API changes.

## Security Requirements

- Admin auth required on all endpoints.
- End-user auth required on inbox and preference endpoints.
- Server-side validation for subject/message length and schedule time.
- Campaign payload stores only normalized filters, never raw query operators from clients.
- Audit rows are append-only.
- Template deletion is blocked when referenced by campaigns.
- Worker claim flow uses lock fields on scheduled campaigns to reduce duplicate execution.
- Quiet-hours and opt-out suppression happen server-side, never in the client.
- Admin visibility uses append-only operational telemetry collections rather than relying on transient logs.

## Implementation Status

### Phase 1: Notification Orchestration Foundation

Deliverables:

- Notification schemas and service layer.
- Mongo indexes.
- Admin REST APIs for templates, campaigns, and audience preview.
- Admin notifications page wired to real APIs.
- Backend regression tests.

Acceptance:

- Admin can create, edit, delete, and reuse templates.
- Admin can preview audience counts.
- Admin can create immediate and scheduled campaigns.
- Campaign history persists across reloads.

Status: complete for in-app channel.

### Phase 2: Execution Worker And Delivery Adapters

Deliverables:

- Scheduled campaign worker.
- Provider adapter interface.
- Delivery attempt rows.
- Delivery attempt rows.
- Manual worker trigger endpoint.
- Worker-run telemetry and admin alert feed.

Acceptance:

- Scheduled campaigns execute without manual intervention.
- Delivery failures are visible to admins.

### Phase 3: User Preferences And In-App Inbox

Deliverables:

- User notification preferences.
- Quiet hours and suppression rules.
- In-app notification center.
- Per-user read state.

Acceptance:

- Users can manage opt-in scope.
- Campaign fan-out respects preferences.

Status: complete for in-app channel.

### Phase 4: Service Extraction

Deliverables:

- Dedicated notification service.
- Worker and API separation.
- Event-driven integration hooks.

Acceptance:

- Existing admin UI keeps working with the same contract.
- Monolith no longer owns notification persistence directly.

## Operational Logging Collections

- `notification_audit_log`: admin-authored lifecycle actions.
- `notification_deliveries`: end-user inbox records and read state.
- `notification_delivery_attempts`: worker and adapter execution telemetry.
- `notification_worker_runs`: polling-cycle level worker visibility.
- `admin_alerts`: unread operational alerts shown in admin UI.
- `notification_preferences`: durable user opt-in and quiet-hours state.

## Implementation Notes

- Keep response models intentionally small and UI-oriented.
- Use derived recipient counts rather than storing raw recipient ID lists in campaign records.
- Preserve shared delivery execution for both immediate and scheduled campaigns so behavior does not diverge.
- Use UTC timestamps everywhere and apply quiet-hours using the user preference timezone.
- Keep adapters narrow so future email/SMS channels can reuse the same campaign and preference model.

## Testing Checklist

- Template CRUD persists and reloads.
- Audience preview reflects user filters.
- Immediate campaign creates per-user delivery rows.
- Scheduled campaign is stored as `scheduled` with future timestamp.
- Worker claims and executes due scheduled campaigns.
- Invalid past schedule is rejected.
- Template delete is blocked if the template is referenced by a campaign.
- Quiet-hours suppression prevents unread inbox fan-out.
- Inbox read actions reduce unread counts.
- Admin summary surfaces unread operational alerts.

## Future Service Extraction Checklist

- Replace service-layer DB calls with transport calls.
- Keep request and response DTOs unchanged.
- Replace the in-process background worker with queue-backed execution.
- Add outbox or event emission for downstream analytics.