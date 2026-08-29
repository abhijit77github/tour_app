# Operator Billing Refinement - Phased Fix Plan

## Objective

This document defines a review-first, implementation-ready phase plan to refine operator billing for correctness, concurrency safety, workflow completeness, and maintainability.

## Implementation Tracking

Last updated: 2026-08-29

Current phase status:

- Phase 0: Complete
- Phase 1: Complete
- Phase 2: Complete
- Phase 3: Complete
- Phase 4: Complete
- Phase 5: In progress (scaffolding started)
- Phase 6: Complete

Current progress notes:

- Completed Phase 1 backend hardening changes for index strategy and race-safe transitions:
  - Added partial unique idempotency index intent for `(operator_profile_id, client_request_id)`.
  - Added partial unique open-order lock intent for one open order per operator.
  - Added duplicate-key race recovery path in plan-order creation.
  - Added compare-and-set cancellation update to avoid overwriting terminal transitions.
- Added dedicated backend tests in `backend/tests/test_operator_billing_orders.py` for race and cancellation conflict paths.
- Implemented Phase 2 core idempotency safeguards:
  - Added `source_order_id` support to plan assignment.
  - Added provider-plan marker `last_fulfilled_order_id` to prevent duplicate grants on retried completion calls.
  - Updated completion flow to call assignment with the current order id.
  - Added idempotency regression test to ensure grant occurs once for repeated completion context.
  - Added conditional final completion write to avoid duplicate `completed` status history entries during concurrent retries.
- Fixed planner quota model drift and duplicate definitions in `backend/models/planner_quota.py`:
  - Removed duplicated/redeclared model blocks.
  - Kept `PlannerRewardGrantRequest` metadata-compatible shape.
  - Updated `PlannerTouristQuotaSettingsUpdate.daily_limit` validation upper bound to `400` for policy consistency.
- Completed Phase 3 API contract alignment:
  - Updated operator analytics ledger call to use `page_size=20`.
- Completed Phase 4 quota consistency cleanup:
  - Aligned planner quota daily limit normalization upper bound with default policy (`400`).
- Started Phase 5 payment workflow scaffolding:
  - Added operator endpoint `PATCH /operator/billing/orders/{order_id}/payment-state` to attach gateway references on open plan orders.
  - Added guarded state progression from `pending_payment` to `payment_pending` when gateway session/order references are attached.
  - Added tests for payment-state update success path and terminal-state rejection.
  - Added payment adapter scaffold `backend/utils/payment_provider.py` and wired order creation response to include provider-agnostic `checkout` payload.
  - Added regression test ensuring order-creation response includes checkout scaffold metadata.
  - Added webhook endpoint `POST /operator/billing/webhooks/{provider}` with:
    - provider-aware signature verification hooks,
    - idempotent webhook event persistence (`billing_webhook_events` collection),
    - payment-success transition to `payment_received/authorized` for matching open orders,
    - duplicate-event acknowledgement semantics.
    - failed-payment transition hook (`order_status=failed`, `payment_status=failed`) for matched open orders.
    - refund transition hook (`payment_status=refunded`) with state-safe handling for completed vs non-completed orders.
  - Added startup indexes for webhook processing safety and lookup.
  - Added webhook tests for signature rejection and duplicate-event idempotency behavior.
  - Added webhook tests for failure and refund transition paths.
  - Added stale unpaid plan-order expiry helper and admin trigger endpoint (`POST /admin/billing/plan-orders/expire-stale`).
  - Added index support for stale-order scans (`order_status`, `expires_at`).
  - Added tests for expiry helper behavior and admin endpoint response counts.
  - Added admin webhook-event observability endpoint (`GET /admin/billing/webhook-events`) with provider/order/event/processed filters.
  - Added admin webhook-event detail endpoint (`GET /admin/billing/webhook-events/{idempotency_key}`) for direct event drill-down.
  - Added settlement handoff enrichment in admin order completion: auto-resolves related webhook event details when request payload omits payment references.
  - Added webhook event retention control:
    - new config `billing_webhook_event_retention_days` (default `180`),
    - startup TTL index `billing_webhook_events_created_at_ttl` on `billing_webhook_events.created_at`.
  - Completed this cycle:
    - added explicit refund-credit compensation scaffolding:
      - new admin endpoint `POST /admin/billing/plan-orders/{order_id}/refund-compensation`,
      - idempotent compensation guard keyed by `(operator_profile_id, source_reference_type=refund_compensation, source_reference_id=order_id)`,
      - provider-plan credit increment + refund ledger entry on first application only.
    - added replay-safe admin webhook reprocess endpoint for reconciliation:
      - new endpoint `POST /admin/billing/webhook-events/{idempotency_key}/reprocess`,
      - shared webhook-transition utility used by both operator webhook ingestion and admin reprocess,
      - reprocess audit trail persisted in webhook event document (`reprocess_history`, `last_reprocessed_at`, `last_reprocessed_by`).
- Completed Phase 6 datetime maintainability cleanup:
  - Replaced dynamic datetime imports in admin billing plan handlers.
  - Verification blocker in initial shell was resolved after switching to `.venv` test runs.
- Runtime verification checkpoint:
  - Backend health check returned `200` from `/health`.
  - OpenAPI check returned `200` and includes all latest billing routes, including:
    - `/admin/billing/webhook-events/{idempotency_key}/reprocess`
    - `/admin/billing/plan-orders/{order_id}/refund-compensation`
- Local runtime smoke status:
  - Backend service is reachable at `http://localhost:8808` (`/health` and `/openapi.json` returned `200`).
  - Running OpenAPI now reflects latest changes:
    - `PlannerTouristQuotaSettingsUpdate.daily_limit.maximum = 400`
    - `/operator/billing/orders/{order_id}/payment-state` is present
    - `/operator/billing/webhooks/{provider}` is present
  - Live webhook safety probe result:
    - `POST /operator/billing/webhooks/razorpay` returned `503 Webhook secret not configured` without secrets, which is the expected secure default.
  - Test validation checkpoint:
    - `python -m unittest backend.tests.test_operator_billing_orders` in `.venv` passed (`21 tests`, `OK`).
  - Live endpoint visibility checkpoint:
    - `/admin/billing/webhook-events` is present in running OpenAPI.
    - `/admin/billing/webhook-events/{idempotency_key}` is present in running OpenAPI.
  - Unauthenticated probe to the new payment-state route returned `401` (expected auth gate), confirming route registration in the live service.
- Added strict provider-integration checklist section for next execution cycle after provider selection.
- Started credit-system gap remediation implementation (Phase A):
  - refund compensation flow now uses order-level lifecycle markers (`processing` -> `applied`/`failed`) to prevent duplicate concurrent credit grants,
  - compensation ledger entries now include deterministic idempotency keys,
  - startup index added for `credit_ledger.idempotency_key` unique (partial),
  - admin compensation response differentiates `already_compensated` vs `compensation_in_progress`,
  - regression tests expanded for idempotent replay and in-progress lock behavior.
- Started credit-system gap remediation implementation (Phase B):
  - added deterministic `billing_event_idempotency_key` linkage on debit ledger entries created from billable events,
  - added unique partial index guard `credit_ledger_billing_event_idempotency_key_debit_unique` to prevent duplicate debits for a single billable event,
  - added admin reconciliation endpoint `GET /admin/billing/reconciliation/credit-events` for missing/mismatched/orphan debit detection,
  - added regression tests for reconciliation missing-debit and orphan-debit reporting,
  - expanded planner billing test to assert ledger-to-event linkage key presence.
  - added replay-safe repair endpoint `POST /admin/billing/reconciliation/credit-events/repair` for partial-failure recovery of event metadata from debit ledger links,
  - added tests covering orphan-debit repair and credit-mismatch repair scenarios.
- Started credit-system gap remediation implementation (Phase C):
  - codified search click dedupe policy into explicit config:
    - `billing_search_click_dedupe_minutes` (window control),
    - `billing_search_click_identity_mode` (`session_first`/`request_first`/`fingerprint_only`),
  - codified planner impression idempotency granularity into explicit config:
    - `billing_planner_impression_scope` (`session`/`daily`/`request`),
  - codified refund compensation policy mode into explicit config:
    - `billing_refund_compensation_mode` (`manual` default, supports `automatic`),
  - wired verified refund webhook flow to auto-apply compensation only when mode is `automatic`,
  - persisted webhook processing metadata with compensation mode/result for auditability,
  - wired planner impression event reference generation to the new policy helper,
  - added policy-control unit tests for both configuration surfaces.
  - added webhook tests verifying manual default (no auto compensation) and automatic mode compensation behavior.
- Started credit-system gap remediation implementation (Phase D):
  - added anomaly counters endpoint `GET /admin/billing/reconciliation/credit-events/anomalies` covering duplicate attempts, compensation failures/in-progress, and mismatch totals,
  - added unresolved mismatch export endpoint `GET /admin/billing/reconciliation/credit-events/export` (`csv`/`json`),
  - added compensation duplicate-attempt telemetry fields on plan orders,
  - added runbook section for reconciliation and compensation retry procedures in payment integration guide,
  - added regression tests for anomaly counter and export behavior.
  - integrated Admin Financial UI reconciliation controls:
    - anomaly counters and unresolved-row preview panel,
    - repair trigger action,
    - CSV/JSON export actions,
    - frontend production build verification (`npm run build`) passed.

## Scope Summary

Priority order:

1. Data integrity and race-condition hardening
2. Exactly-once fulfillment and ledger safety
3. Frontend/backend contract alignment
4. Quota/pricing consistency cleanup
5. Payment workflow scaffolding
6. Maintainability cleanup

---

## Phase 0 - Baseline and Freeze

Target duration: 0.5 day

### Goals

- Confirm current operator billing API/UI contracts.
- Lock a backward-compatibility policy for changes.
- Establish explicit test gates for every implementation phase.

### Tasks

- Capture baseline endpoint behavior and expected responses.
- Confirm invariants:
  - One open plan order per operator.
  - Idempotent create via client request id.
  - Exactly-once plan fulfillment per order.
- Finalize acceptance checklist for each phase.

### Exit Criteria

- Scope and sequence approved.
- Compatibility policy approved.
- Test gate list approved.

---

## Phase 1 - Data Integrity and Concurrency Hardening

Target duration: 1-2 days

### Goals

- Prevent duplicate open plan orders under concurrency.
- Prevent unsafe state overwrites in cancel/transition flows.

### Tasks

- Add database constraints:
  - Unique partial index on `(operator_profile_id, client_request_id)` where `client_request_id` exists and is non-empty.
  - Unique partial index to enforce one open order per operator.
- Refactor order creation from check-then-insert to atomic create-or-reuse behavior.
- Make cancel operation compare-and-set safe by enforcing allowed current states in update filters.
- Return deterministic conflict responses when transition races happen.

### Validation

- Idempotent create retry tests.
- Duplicate-create race tests.
- Cancel-vs-complete crossing race tests.

### Exit Criteria

- No duplicate open orders in concurrent tests.
- Cancel cannot overwrite terminal/completed states.
- Tests pass consistently.

---

## Phase 2 - Fulfillment Idempotency and Ledger Safety

Target duration: 1-1.5 days

### Goals

- Ensure plan activation and credit grants happen exactly once per order.

### Tasks

- Add explicit fulfillment marker(s) bound to order identity.
- Guard settlement path with once-only atomic transitions.
- Prevent duplicate credit grants from retried completion calls.
- Normalize repeated completion responses to idempotent behavior.

### Validation

- Repeated completion-call tests (same and varied metadata).
- Single ledger grant assertion per order.
- Terminal-state rejection regression tests.

### Exit Criteria

- Exactly-once fulfillment behavior validated.
- No duplicate ledger grant entries on retries.

---

## Phase 3 - API Contract Alignment and UX Consistency

Target duration: 0.5-1 day

### Goals

- Align frontend query parameters and backend contract usage.
- Remove silent fallbacks that can confuse operators.

### Tasks

- Align ledger pagination params (`page_size`/cursor) across operator billing UI and API.
- Standardize cursor pagination handling in operator billing views.
- Optionally add temporary backend aliasing for safe rollout compatibility.

### Validation

- API integration tests for pagination parameters.
- Operator UI smoke verification for plan orders and ledger screens.

### Exit Criteria

- Frontend calls match documented backend contracts.
- Pagination behavior is predictable and documented.

---

## Phase 4 - Quota and Pricing Consistency Cleanup

Target duration: 0.5 day

### Goals

- Eliminate default-vs-normalization policy mismatches.

### Tasks

- Decide intended planner quota policy bounds with product input.
- Align defaults, validation limits, and normalization caps.
- Add migration/normalization rules for existing stored settings if required.

### Validation

- Settings round-trip tests.
- Boundary-value tests for min/max behaviors.

### Exit Criteria

- One consistent quota policy across defaults, persistence, and runtime.

---

## Phase 5 - Payment Workflow Scaffolding

Target duration: 2-4 days (can be split into a separate milestone)

### Goals

- Move from placeholder plan-order flow toward provider-integrated lifecycle.

### Tasks

- Add payment provider adapter interface.
- Implement checkout/session attach endpoint.
- Implement signature verification and webhook handlers.
- Implement replay-safe webhook processing and settlement idempotency.
- Add stale pending-order expiry worker and refund-state handling hooks.

### Validation

- Adapter contract tests.
- Webhook replay/idempotency tests.
- End-to-end sandbox payment lifecycle tests.

### Exit Criteria

- Provider flow works in sandbox.
- Replay-safe settlement behavior verified.

### Strict Implementation Checklist (Provider Integration)

Execution gate:

- [ ] Provider is selected and documented (`razorpay` or alternative), with explicit MVP scope (one-time order only vs recurring).

Blockers (must be complete before merge):

- [ ] Secrets/config finalized per environment:
  - [ ] API key(s), webhook secret(s), callback URL(s), allowed origin(s)
  - [ ] missing-secret behavior confirmed (safe fail)
- [ ] Real checkout/session creation implemented in provider adapter:
  - [ ] create gateway order/session from internal order
  - [ ] persist gateway ids with idempotent order update
  - [ ] timeout and retry policy defined with deterministic request id
- [ ] Signature verification uses provider-native format and headers:
  - [ ] invalid signature rejection test
  - [ ] missing signature rejection test
- [ ] Webhook event mapping and transitions finalized:
  - [ ] success -> `payment_received`/`authorized`
  - [ ] failure -> `failed`
  - [ ] refund -> `refunded` with safe terminal handling
- [ ] Settlement invariants finalized:
  - [ ] exact trigger for fulfillment (`authorized` vs `captured`)
  - [ ] exactly-once fulfillment confirmed under retries/concurrency
- [ ] Refund compensation policy finalized:
  - [ ] manual vs automatic compensation decision documented
  - [ ] partial-refund behavior documented
- [ ] Index and migration verification:
  - [ ] idempotency/open-order/webhook lookup/TTL indexes verified in runtime DB
  - [ ] startup or migration check fails loudly when required indexes are missing
- [ ] API docs updated:
  - [ ] operator payment flow responses
  - [ ] admin replay and refund-compensation actions

Quality gates (must pass before release):

- [ ] Unit tests for adapter, event parsing, and transition guards.
- [ ] Integration tests with provider sandbox payload fixtures.
- [ ] End-to-end sandbox lifecycle test:
  - [ ] create order -> checkout -> success webhook -> admin completion
  - [ ] refund webhook -> compensation path (per policy)
- [ ] Negative/replay tests:
  - [ ] duplicate webhook (no double mutation)
  - [ ] tampered signature
  - [ ] stale order expiry + replay interaction

Operational readiness (required for production cutover):

- [ ] Structured logs include `order_code`, `event_id`, `idempotency_key`.
- [ ] Metrics/alerts in place for webhook failure, replay count, settlement latency.
- [ ] Runbook documented for manual replay/reconciliation and failure recovery.
- [ ] Rollout guard in place (feature flag or environment gate) with sandbox soak window.

---

## Phase 6 - Maintainability and Cleanup

Target duration: 0.5 day

### Goals

- Improve readability and consistency after risk fixes.

### Tasks

- Replace dynamic datetime import patterns with standard imports.
- Perform minor router consistency cleanup.
- Update billing docs to reflect final behavior and transitions.

### Exit Criteria

- No behavior change, improved maintainability.
- Documentation synchronized with implementation.

---

## Cross-Phase Testing Strategy

- Create dedicated operator billing backend test module(s) for route and lifecycle coverage.
- Add a small concurrency-focused test suite for idempotency and state transitions.
- Keep RBAC/auth/reporting tests in CI gate to avoid regressions.
- Add ledger correctness assertions for no duplicate grants/debits.

## Credit System Gap Remediation Checklist

Status: Added for execution and tracking.

### Phase A - Integrity Hardening (Start Here)

- [x] Make refund compensation exactly-once under concurrency.
- [x] Add DB-level idempotency guard for compensation ledger writes.
- [x] Add failure-safe order markers for compensation lifecycle (`processing`, `applied`, `failed`).
- [x] Add regression tests for replay/race paths.

### Phase B - Debit Consistency and Reconciliation

- [x] Add deterministic link between billable event and ledger debit.
- [x] Add reconciliation query/endpoint for mismatched debit vs event records.
- [x] Add tests for partial-failure recovery semantics.

### Phase C - Policy and Billing Behavior

- [x] Decide and document click dedupe window policy (fraud-control vs revenue fidelity).
- [x] Decide and document planner impression billing granularity.
- [x] Define refund compensation policy mode (manual-only vs automatic).

### Phase D - Observability and Ops Controls

- [x] Add anomaly counters for duplicate-attempt, compensation-failure, and mismatch counts.
- [x] Add admin view/export for unresolved billing mismatches.
- [x] Add runbook section for compensation retry and audit procedures.
- [x] Wire Admin Financial UI controls for anomaly refresh, repair action, and CSV/JSON exports.

## Suggested PR Sequence

1. PR-A: Phase 1 hardening + tests
2. PR-B: Phase 2 fulfillment idempotency + tests
3. PR-C: Phase 3 contract alignment + UI/API tests
4. PR-D: Phase 4 quota consistency + tests
5. PR-E: Phase 5 payment scaffolding + integration tests
6. PR-F: Phase 6 cleanup + docs sync

## Review Decision Points

- Approve strict invariant: one open plan order per operator.
- Approve exactly-once fulfillment as non-negotiable.
- Confirm whether Phase 5 is in current milestone or next milestone.
- Confirm whether temporary compatibility aliasing is acceptable in Phase 3.
