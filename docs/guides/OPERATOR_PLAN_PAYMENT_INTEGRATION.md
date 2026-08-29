# Operator Plan Order and Payment Integration Guide

## Purpose

This guide documents the operator-side paid credit-plan purchase flow that now exists before real gateway integration.

The system now supports:

- creation of operator plan purchase orders
- order tracking on the operator UI
- cancellation before settlement
- admin-side settlement and fulfillment
- activation of the purchased plan through the existing hardened credit-assignment path

The only missing piece is the external payment provider integration itself.

## Current Scope

Implemented now:

- operator can create a purchase order for an active paid billing plan
- only one open plan order is allowed per operator at a time
- each order stores a server-side plan snapshot so later plan edits do not change what was sold
- operator can list and cancel unpaid orders
- operator can attach gateway session/order/payment references to open plan orders
- admin can list plan orders and complete them after payment verification
- plan completion activates the plan and grants credits through the existing `assign_plan_to_operator(...)` helper
- status history is persisted on the order for traceability
- provider webhook endpoint is available with signature verification hooks and idempotent event persistence

Not implemented yet:

- Razorpay, Stripe, or PayU checkout session creation
- refund handling
- automatic expiry worker for stale pending orders (manual admin-triggered expiry endpoint exists)

Partially implemented scaffolding:

- webhook signature verification hooks
- webhook route with idempotent event persistence
- webhook-driven interim payment-state transitions (`payment_received`, `failed`, `refunded`)
- webhook event retention TTL via `billing_webhook_event_retention_days` configuration

## Collections

### `plan_orders`

New collection for operator credit-plan purchases.

Core fields:

- `order_code`: server-generated unique business identifier
- `operator_profile_id`
- `operator_user_id`
- `organization_id`
- `plan_code`
- `plan_snapshot`
- `amount`
- `currency`
- `payment_provider`
- `order_status`
- `payment_status`
- `fulfillment_status`
- `client_request_id`
- `payment_reference`
- `gateway_session_id`
- `gateway_order_id`
- `gateway_payment_id`
- `gateway_metadata`
- `subscription_snapshot`
- `status_history`
- `expires_at`
- `created_at`
- `updated_at`
- `settled_at`
- `settled_by`
- `completed_at`
- `cancelled_at`

### Existing collections reused

- `billing_plans`: source plan definitions
- `provider_plans`: active operator subscription and current credits
- `credit_ledger`: immutable credit movement log

## Status Model

### `order_status`

Open states:

- `pending_payment`
- `payment_pending`
- `payment_received`
- `fulfillment_pending`

Terminal states:

- `completed`
- `cancelled`
- `expired`
- `failed`

### `payment_status`

- `not_started`
- `pending`
- `authorized`
- `paid`
- `failed`
- `cancelled`
- `refunded`

### `fulfillment_status`

- `not_started`
- `pending`
- `completed`
- `failed`

## Backend Endpoints

### Operator endpoints

#### `GET /operator/billing/plans`

Returns active billing plans plus payment-provider configuration hints.

Response additions:

- `payment_providers`
- `gateway_status`
- `message`

#### `GET /operator/billing/plan`

Returns current subscription state and now also includes:

- `open_plan_order`

#### `GET /operator/billing/orders`

Lists the current operator's plan purchase orders.

#### `POST /operator/billing/orders`

Creates a new paid-plan purchase order.

Request body:

```json
{
  "plan_code": "PRO",
  "payment_provider": "razorpay",
  "client_request_id": "2f6b9eb7-09d2-4cf2-9c92-9d8c7d8b1f2f"
}
```

Behavior:

- rejects `FREE`
- requires active plan definition
- reuses existing order if `client_request_id` repeats for the same operator
- blocks creation if another open plan order already exists
- stores plan snapshot at creation time

Response:

```json
{
  "message": "Plan order created. Attach the payment gateway checkout session in the next integration step.",
  "order": {"_id": "...", "order_code": "PORD-...", "order_status": "pending_payment"},
  "gateway_status": "not_configured",
  "next_action": "Create a provider checkout/order session, update the order with gateway references, then settle the order after payment verification.",
  "created": true
}
```

#### `DELETE /operator/billing/orders/{order_id}`

Cancels an unpaid or unfulfilled order.

Allowed states:

- `pending_payment`
- `payment_pending`
- `payment_received`

#### `PATCH /operator/billing/orders/{order_id}/payment-state`

Attaches provider references on open plan orders.

Request body supports:

- `gateway_session_id`
- `gateway_order_id`
- `payment_reference`
- `gateway_metadata`

Behavior:

- only allowed for open plan-order states
- promotes `payment_status` from `not_started` to `pending` when session/order references are attached
- can move `order_status` from `pending_payment` to `payment_pending`

### Webhook endpoint

#### `POST /operator/billing/webhooks/{provider}`

Provider webhook scaffold endpoint with idempotent event handling.

Behavior:

- validates provider-specific signature headers using configured webhook secrets
- stores idempotency record in `billing_webhook_events`
- for payment-success events, transitions matching open orders to `payment_received` / `authorized`
- duplicate events are acknowledged without reapplying state changes

### Compatibility endpoint

#### `POST /operator/billing/subscribe`

This route now acts as a compatibility shim and creates a plan order with default provider `razorpay`.

Do not use this for new integrations.

### Admin endpoints

#### `GET /admin/billing/plan-orders`

Lists plan orders for admin review.

Supported filters:

- `order_status`
- `payment_status`
- `limit`

#### `POST /admin/billing/plan-orders/{order_id}/complete`

Marks payment as settled and fulfills the order.

Request body:

```json
{
  "payment_reference": "manual-ref-001",
  "gateway_payment_id": "pay_123",
  "gateway_order_id": "order_123",
  "settlement_notes": "Verified via provider dashboard",
  "gateway_metadata": {
    "provider_event": "payment.captured"
  }
}
```

Behavior:

- if payment reference fields are omitted, completion attempts to resolve related webhook event data (`payment_reference`, `gateway_payment_id`, `gateway_order_id`) using order/webhook linkage
- settlement metadata is enriched with webhook context when available

#### `GET /admin/billing/webhook-events`

Lists persisted webhook events for reconciliation and diagnostics.

Supported filters:

- `provider`
- `order_code`
- `event_id`
- `processed`
- `limit`

#### `GET /admin/billing/webhook-events/{idempotency_key}`

Returns a single webhook event record for reconciliation drill-down.

#### `GET /admin/billing/reconciliation/credit-events`

Returns unresolved credit-event anomalies:

- missing debit for billable event
- duplicate debit rows for one event link
- credit mismatch between event and ledger
- orphan debits with no matching billable event

#### `POST /admin/billing/reconciliation/credit-events/repair`

Runs replay-safe repair for repairable mismatches (event metadata correction from linked debit records).

#### `GET /admin/billing/reconciliation/credit-events/anomalies`

Returns anomaly counters for operations monitoring, including:

- duplicate compensation attempts
- compensation failures and in-progress states
- mismatch totals and mismatch breakdown

#### `GET /admin/billing/reconciliation/credit-events/export`

Exports unresolved reconciliation rows for admin review and audit.

Supported query params:

- `days`
- `limit`
- `format` (`csv` or `json`)

#### `POST /admin/billing/plan-orders/{order_id}/refund-compensation`

Manual compensation path for refunded + completed orders.

Behavior:

- idempotent against repeated calls
- returns explicit status: processed, already applied, or in progress

## Reconciliation and Compensation Runbook

Use this flow for day-to-day operations and incident response.

### 1. Check anomaly counters

Call `GET /admin/billing/reconciliation/credit-events/anomalies` with the desired `days` window.

If `mismatch_count > 0` or `compensation_failure_count > 0`, continue to the next step.

### 2. Inspect unresolved rows

Call `GET /admin/billing/reconciliation/credit-events` for detailed records.

Optional export for ops handoff:

- `GET /admin/billing/reconciliation/credit-events/export?format=csv`

### 3. Run repair for repairable mismatches

Call `POST /admin/billing/reconciliation/credit-events/repair`.

Review response:

- `repaired`
- `unresolved_missing_debits`
- `unresolved_orphan_debits`
- `skipped_duplicate_debits`

### 4. Handle unresolved items manually

For `unresolved_missing_debits` or `skipped_duplicate_debits`:

- verify source event timeline and operator credit state
- apply explicit admin credit adjustment only after audit confirmation

### 5. Refund compensation operations

Policy mode is controlled by `billing_refund_compensation_mode`:

- `manual` (default): use `POST /admin/billing/plan-orders/{order_id}/refund-compensation`
- `automatic`: verified refund webhooks attempt auto compensation

If auto mode is enabled and an order remains uncompensated, retry manual compensation endpoint once before raising incident.

### 6. Audit trail checkpoints

For each incident record:

- order code
- webhook event id or idempotency key
- reconciliation issue type
- action taken (repair/manual adjustment)
- actor id and timestamp

Handoff behavior now validated in tests:

- provider webhook marks payment state on matching plan order
- admin completion can be executed without manually re-entering payment references
- completion enriches settlement metadata using the related webhook event

- rejects terminal non-completed orders
- transitions order to `fulfillment_pending`
- uses `assign_plan_to_operator(...)`
- resets credits to the purchased plan's included credits
- writes ledger deltas through existing credit-ledger logic
- finalizes order as `completed`

## Fulfillment Path

The fulfillment path intentionally reuses the existing hardened billing logic.

Sequence:

1. Operator creates order.
2. Gateway integration later creates external checkout session or gateway order.
3. Provider callback or manual verification confirms payment.
4. Backend calls `POST /admin/billing/plan-orders/{order_id}/complete` or the same helper logic from a future webhook handler.
5. `complete_operator_plan_order(...)` moves the order into `fulfillment_pending`.
6. `assign_plan_to_operator(...)` activates the purchased plan and grants the plan credits.
7. Credit delta is written to `credit_ledger`.
8. Order is finalized as `completed`.

## Security and Consistency Rules

These rules should not be relaxed during payment integration.

- Only one open plan order per operator at a time.
- Only paid plans create purchase orders.
- Plan fulfillment must stay server-side.
- Gateway identifiers must never be trusted from the browser without server verification.
- Plan credits must only be granted through `assign_plan_to_operator(...)`.
- Repeated completion calls must remain idempotent at the order level.
- Gateway payloads stored in `gateway_metadata` should be redacted before persistence when they include unnecessary sensitive data.

## Future Payment Integration Steps

### Recommended integration shape

Add a backend payment adapter layer, not direct browser-to-provider fulfillment.

Recommended sequence:

1. Operator calls `POST /operator/billing/orders`.
2. Backend creates provider-specific checkout/order/session using the chosen provider.
3. Backend stores:
   - `gateway_session_id`
   - `gateway_order_id`
   - `payment_status = pending`
   - `order_status = payment_pending`
4. Browser is redirected to provider checkout using only server-created identifiers.
5. Provider webhook hits a dedicated backend webhook route.
6. Backend verifies signature and payment amount.
7. Backend maps webhook to `plan_orders` row.
8. Backend calls the same completion helper used by admin completion.

### Required future endpoints or services

You can keep the current order model and add only these pieces:

- provider checkout-session creation service
- provider webhook handlers
- optional admin refund/cancel actions
- scheduled expiry job for stale open orders

## Operator UI Contract

The operator promotions/billing page now assumes:

- plan purchase buttons create plan orders, not direct plan changes
- `open_plan_order` is the banner source for current pending purchase state
- plan order history is displayed separately from promotion order history
- operator can cancel open plan orders before settlement

## Admin UI / Ops Contract

Even without admin UI wiring, backend support now exists for:

- reviewing plan orders
- filtering by status
- completing orders after manual payment verification

A future admin UI can safely bind to `GET /admin/billing/plan-orders` and `POST /admin/billing/plan-orders/{order_id}/complete`.

## Validation Completed

The following behaviors were validated live after implementation:

- operator plan order creation returns `pending_payment`
- admin completion moves order to `completed`
- payment status becomes `paid`
- operator plan changes after completion
- operator credit balance resets to the purchased plan credits
- open-order duplication is blocked
- operator cancellation succeeds for unpaid orders

## Files Touched

Primary implementation files:

- `backend/models/billing.py`
- `backend/utils/billing.py`
- `backend/routers/operator_billing.py`
- `backend/routers/admin_billing.py`
- `backend/main.py`
- `frontend/src/views/OperatorPromotions.vue`

Use this guide as the entry point when adding Razorpay, Stripe, or PayU checkout and webhook settlement later.
