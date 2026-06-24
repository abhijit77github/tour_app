# Provider Paid Distribution Plan

## Purpose

Define a production-ready paid distribution system for operators so they can:

- buy promoted visibility in search and discovery surfaces
- participate in higher-value planner and quote-request distribution
- understand exactly what they are paying for
- receive auditable reporting for impressions, clicks, qualified leads, and conversions

This document is intentionally implementation-oriented. It is written against the current codebase so work can proceed phase by phase after review.

## Product Positioning

The platform should not require providers to pay merely to exist. Basic discovery should remain available organically. Paid services should monetize distribution and qualified demand, not profile creation.

The commercial model should be:

- Free organic listing: profile, serving areas, reviews, standard quote participation
- Paid distribution: promoted search, planner inclusion, quote-request priority/unlock, analytics, premium profile tools
- Optional success monetization later: booking commission or accepted-quote success fee

## Current Implementation Baseline

The repository already contains an early promotions foundation:

- Promotion package catalog and purchase orders exist in:
  - [backend/models/promotion_package.py](/home/ubuntu/abhijit/tour_app/backend/models/promotion_package.py)
  - [backend/routers/operator_promotions.py](/home/ubuntu/abhijit/tour_app/backend/routers/operator_promotions.py)
- Location promotion entity and CPC click tracking exist in:
  - [backend/models/promotion.py](/home/ubuntu/abhijit/tour_app/backend/models/promotion.py)
  - [backend/routers/operators.py](/home/ubuntu/abhijit/tour_app/backend/routers/operators.py)
- Admin creation and activation of location promotions exist in:
  - [backend/routers/admin.py](/home/ubuntu/abhijit/tour_app/backend/routers/admin.py)
  - [frontend/src/views/AdminPromotions.vue](/home/ubuntu/abhijit/tour_app/frontend/src/views/AdminPromotions.vue)
- Operator purchase UI exists in:
  - [frontend/src/views/OperatorPromotions.vue](/home/ubuntu/abhijit/tour_app/frontend/src/views/OperatorPromotions.vue)
- Search UI already shows promoted inventory and tracks promotion clicks:
  - [frontend/src/views/Search.vue](/home/ubuntu/abhijit/tour_app/frontend/src/views/Search.vue)

Important current limitations:

- payment is not integrated yet; purchase orders are placeholders for future gateway checkout
- CPC tracking exists only for promoted search result clicks
- there is no credit wallet, billing ledger, or invoice model yet
- planner and quote surfaces are not yet monetized with auditable event billing
- fraud controls and bot suppression are minimal

This plan extends that system rather than replacing it.

## Commercial Recommendation

### First Commercial Version

Launch a hybrid model:

- base subscription plan unlocks premium distribution surfaces
- monthly included credits cover measurable paid actions
- top-up credits available when included credits are exhausted
- optional booking success fee deferred to a later phase

This is the best balance between:

- simple commercial explanation for providers
- controlled spend
- auditable usage
- future expansion to planner and quote distribution

## Paid Surfaces

### 1. Promoted Search Listing

Provider can appear in promoted slots in destination/operator search.

Current fit with codebase:

- already partially implemented through `location_promotions`
- ranked by priority and bid amount in [backend/routers/operators.py](/home/ubuntu/abhijit/tour_app/backend/routers/operators.py)

Recommended billing unit:

- phase 1: CPC on unique profile click from promoted search
- optional CPM reporting only, not billing, in phase 1

### 2. Promoted Planner Inclusion

Provider can be surfaced in a promoted but relevance-gated planner shortlist for matching trip briefs.

Recommended billing unit:

- qualified planner click
- higher credit weight than plain search click

### 3. Quote Request Priority or Unlock

Provider gets earlier or premium access to matching quote requests, or can consume credits to unlock high-fit requests.

Recommended billing unit:

- per unlocked qualified quote lead
- optionally weighted by completeness of the quote request

### 4. Premium Profile Tools

Not billed by event. Included by plan.

Examples:

- richer gallery/media
- profile badge
- enhanced analytics
- response tools
- team access later

## Quantization Strategy

The paid system must bill on explicit, auditable events.

### Billable Event Types

#### Impression

Definition:

- promoted provider card was rendered in a designated paid slot
- slot was visible in viewport for a minimum threshold
- event passed bot and duplicate suppression checks

Use:

- reporting in phase 1
- optional CPM billing later

#### Profile Click

Definition:

- user clicked from promoted card into provider profile or detailed view

Use:

- primary search monetization event in phase 1

#### Intent Click

Definition:

- user clicked a high-intent CTA from a provider card or profile

Examples:

- add to cart
- request quote
- start chat
- call or WhatsApp

Use:

- planner monetization event
- premium reporting funnel stage

#### Qualified Lead

Definition:

- a real quote request or inquiry is delivered to or unlocked by a provider
- request includes minimum required fields and passes spam checks

Use:

- quote-marketplace billing in later phases

#### Conversion

Definition:

- accepted quote or completed booking tied to a provider and attributable surface

Use:

- success fee in later phase

## Recommended Credit Weights

Credits are the simplest operator-facing abstraction for mixed paid surfaces.

Suggested initial weighting:

- 1 credit: unique promoted search profile click
- 2 credits: unique planner profile click
- 3 credits: planner add-to-cart or quote-intent click
- 4 credits: unlocked standard qualified quote request
- 6 credits: unlocked premium quote request with dates, budget, travelers, and attached itinerary

These values should be configurable from admin settings, not hardcoded in ranking logic.

## Plans

### Free

- organic listing only
- standard profile
- standard quote participation
- no promoted search
- no planner promotion
- no lead credits
- limited analytics

### Growth

- eligible for promoted search
- eligible for promoted planner placement
- includes monthly credits
- enhanced analytics
- featured/profile badge subject to quality thresholds

### Pro

- higher monthly credit allowance
- higher caps on promoted distribution
- quote request unlock credits
- richer analytics and destination-level performance breakdown
- future team seats and automation tools

### Enterprise Later

- multi-branch operators
- account management
- invoicing
- API/webhook exports

## Ranking and Relevance Controls

Payment must not fully override quality and relevance.

Use a blended score:

$$
final\_score = 0.55 \cdot relevance + 0.20 \cdot quality + 0.15 \cdot performance + 0.10 \cdot paid\_boost
$$

Where:

- `relevance`: destination, service type, budget fit, brief fit, itinerary fit
- `quality`: rating, response quality, profile completeness, admin trust flags
- `performance`: click-through, lead acceptance, quote response rate, conversion rate
- `paid_boost`: plan entitlement, active campaign, available credits, package priority

Hard rules:

- provider must match serving area
- provider must support requested service type
- provider must not be suspended or downgraded by trust/risk checks
- provider must have available campaign budget or credits for paid delivery

## Security and Abuse Controls

This system is financially sensitive. Treat event collection and payment state as security-critical.

### Core Security Requirements

#### 1. No trust in client-side billing events

Client may suggest context, but server decides whether an event is billable.

Required:

- server-side validation of provider eligibility
- server-side deduplication
- server-side attribution validation
- server-side charge calculation

#### 2. Idempotent billing writes

Any billed event must use an idempotency key derived from:

- event type
- provider/promotion identifier
- surface
- session fingerprint or user id
- normalized time bucket

This prevents double-billing on retries or duplicate clicks.

#### 3. Rate limits

Required on all event ingestion endpoints:

- per IP
- per authenticated user
- per session id
- per provider target

#### 4. Bot and fraud controls

At minimum:

- ignore known bot user agents where possible
- drop implausibly fast repeated clicks
- unique click billing window per user/session
- suspicious IP/device fingerprint monitoring
- anomaly detection for providers with abnormal CTR or self-click patterns

#### 5. Payment webhook trust boundary

When payment is wired later:

- only webhooks may finalize payment status
- webhook signature verification mandatory
- never activate a campaign from client callback alone

#### 6. Principle of least privilege

Separate roles:

- operator can create purchase intent/order and view their own analytics
- admin can approve packages, override campaigns, refund, and review fraud
- background workers can finalize billing aggregation jobs

## Data Model Additions

Do not overload `promotion_events` for everything. Introduce explicit billing and analytics entities.

### Recommended Collections

#### `provider_plans`

Stores active operator subscription state.

Fields:

- operator_profile_id
- plan_code
- status
- billing_cycle_start_at
- billing_cycle_end_at
- auto_renew
- included_credits
- remaining_credits
- created_at
- updated_at

#### `billing_event_log`

Immutable raw billable events.

Fields:

- event_id
- idempotency_key
- operator_profile_id
- promotion_id optional
- plan_id optional
- source_surface: `search | planner | quote`
- event_type: `impression | profile_click | intent_click | qualified_lead | conversion`
- actor_user_id optional
- anonymous_session_id optional
- request_fingerprint
- quoted_units
- credits_charged
- currency optional
- monetary_amount optional
- attribution_context
- risk_flags
- is_billable
- created_at

#### `credit_ledger`

Immutable accounting ledger for credit changes.

Fields:

- operator_profile_id
- entry_type: `grant | reserve | consume | release | refund | adjustment | expiry`
- credits_delta
- balance_after
- source_reference_type
- source_reference_id
- notes
- created_at
- created_by

#### `payment_transactions`

Tracks gateway-side payment records.

Fields:

- order_id
- operator_profile_id
- gateway_provider
- gateway_payment_id
- gateway_order_id
- amount
- currency
- payment_status
- raw_gateway_payload_redacted
- created_at
- updated_at

#### `provider_analytics_daily`

Daily pre-aggregated reporting table.

Fields:

- operator_profile_id
- date
- surface
- impressions
- unique_clicks
- intent_clicks
- qualified_leads
- conversions
- credits_consumed
- spend_amount

## API Design Additions

### Operator APIs

- `GET /operator/billing/plan`
- `GET /operator/billing/credits`
- `GET /operator/billing/ledger`
- `GET /operator/billing/analytics`
- `POST /operator/promotions/topup`
- `GET /operator/promotions/eligibility`

### Event Tracking APIs

Phase 1 can extend existing endpoints, but the end-state should use explicit event endpoints.

- `POST /events/promoted-impression`
- `POST /events/promoted-click`
- `POST /events/planner-intent`
- `POST /events/quote-unlock`

Each must:

- authenticate if user exists, otherwise use server-issued anonymous session id
- enforce replay protection
- return success without revealing billing internals

### Admin APIs

- `GET /admin/billing/plans`
- `POST /admin/billing/plans`
- `PATCH /admin/billing/plans/{plan_id}`
- `GET /admin/billing/ledger`
- `GET /admin/billing/risk-events`
- `POST /admin/billing/adjustments`

## Planner Monetization Rules

The planner should not become a pure ad placement surface.

Rules:

- promoted planner operators are only eligible if they fit the brief
- promoted operators should appear inside a designated promoted subset, not contaminate all ranking blindly
- a planner impression is billed only if the promoted card was actually shown
- a planner click is billable only on unique meaningful interaction
- add-to-cart from planner should be a higher-intent billed event than profile open

Recommendation:

Phase 2 planner billing should bill on unique profile click or add-to-cart, not impression.

## Quote Marketplace Monetization Rules

Quote requests are highest intent and most sensitive.

Rules:

- unlocking a quote lead should consume credits only once per provider per quote
- providers should not be able to unlock quotes outside service area or service type
- quote request must meet minimum quality thresholds before it is billable
- repeated spam or low-quality quote creation from tourists must not generate paid provider charges

Minimum qualified lead threshold:

- at least one destination
- at least one of travel window or duration
- enough details to reasonably respond

Premium qualified lead threshold later:

- dates or date range
- travelers
- budget
- optional itinerary attached

## Phase Plan

### Phase 0: Hardening Existing Promotion Foundation

Goal:

- make current search promotion code safe to extend

Scope:

- review and harden existing search impression and click tracking
- add idempotency protections for click billing
- add fraud/rate-limit hooks
- make impression counting viewport-aware where possible from UI event design
- document current collections and indexes

Deliverables:

- hardened click tracking endpoint
- event idempotency design
- baseline promotion audit logging

### Phase 1: Search Promotion v1

Goal:

- production-ready paid search promotion with plan-gated access

Scope:

- introduce subscription plans and credit ledger
- continue using current package and order flow as acquisition path
- convert packages into credit grants or active campaign entitlements after payment/admin approval
- bill unique promoted search clicks in credits
- build provider analytics dashboard for impressions, clicks, CTR, spend, and remaining credits

Deliverables:

- `provider_plans`
- `credit_ledger`
- `billing_event_log`
- operator billing dashboard
- admin plan configuration

### Phase 2: Planner Promotion v1

Goal:

- monetize planner distribution without degrading relevance

Scope:

- planner-specific eligibility and promoted slot logic
- bill unique planner interactions
- track planner impressions and planner add-to-cart separately
- add planner analytics in operator dashboard

Deliverables:

- planner attribution context
- planner billed events
- operator analytics split by surface

### Phase 3: Quote Lead Unlock v1

Goal:

- charge for qualified quote opportunity delivery

Scope:

- define quote quality thresholds
- allow plans or credit top-ups to unlock premium quote requests
- create lead state machine: eligible, unlocked, responded, expired, refunded if invalid
- admin overrides and refund tooling

Deliverables:

- quote lead billing rules
- unlock endpoints
- quote lead ledger entries

### Phase 4: Payments, Invoices, and Webhooks

Goal:

- move from placeholder purchase order to real payment settlement

Scope:

- Razorpay first, keep abstraction for Stripe and PayU
- signed webhook verification
- invoice generation
- reconciliation jobs
- failed payment and refund handling

Deliverables:

- payment transaction model
- webhook handlers
- invoice records

### Phase 5: Success-Based Monetization

Goal:

- optionally monetize actual outcomes

Scope:

- booking attribution
- accepted-quote attribution
- success fee rules
- dispute and refund policy

Deliverables:

- attribution chain
- commission settlement rules

## Phase 1 Recommended Implementation Sequence

When coding begins after review, implement in this order:

1. Add billing domain models and indexes
2. Add immutable credit ledger and billing event log
3. Add plan configuration and operator plan assignment
4. Harden search click event tracking for unique-billable logic
5. Add server-side credit consumption on valid unique click
6. Add operator analytics endpoints
7. Add operator billing dashboard UI
8. Add admin configuration and audit views

This order keeps money state correct before UI growth.

## Acceptance Criteria for Phase 1

- operator can hold an active paid plan
- operator has visible remaining credits
- promoted search clicks consume credits exactly once per unique qualifying event
- duplicate client retries do not double charge
- non-eligible clicks do not charge
- analytics show daily impressions, unique clicks, CTR, and credits consumed
- admin can inspect ledger and manually adjust credits with audit reason
- payment state still not trusted until webhook confirmation in later phase

## Observability

Add structured logs and metrics for:

- billed events accepted
- billed events rejected
- duplicate event suppression count
- suspicious click rate
- credits consumed per surface
- plan exhaustion events
- quote unlock rejection reasons

Use correlation ids across:

- request
- billing event
- credit ledger entry
- payment transaction

## Privacy and Compliance Notes

- avoid storing raw PII in analytics aggregates
- hash or tokenize session fingerprints where possible
- redact gateway payloads before storage
- define retention window for raw event logs
- ensure admin audit actions are attributable by admin id and timestamp

## Open Product Decisions Requiring Review

These decisions should be finalized before implementation begins:

1. Should free operators still receive all quote requests, or only a limited subset?
2. Should planner promotion be billed on click only, or click plus add-to-cart weighting?
3. Should search promotion remain CPC-only in phase 1, or should plans include fixed impression buckets?
4. Should high-value quote leads consume more credits when an itinerary is attached?
5. Should badge visibility depend purely on payment, or also on quality thresholds like response rate and rating?

## Recommended Decision for First Release

Adopt this launch posture:

- free organic listing remains intact
- paid search promotion bills on unique promoted click only
- planner promotion added in phase 2, not phase 1
- quote lead unlock added in phase 3, not phase 1
- credits are the operator-facing billing unit
- real payment integration is phase 4, but purchase orders remain the acquisition shell until then

This gives a production-safe first slice while keeping the architecture extensible.

## Next Step After Review

If this plan is approved, implementation should begin with Phase 0 and Phase 1 only.

That means:

- harden current promotion event tracking
- introduce plans, credits, and ledger models
- wire search promotion billing against unique clicks
- expose operator analytics and admin controls

No planner billing, quote unlock billing, or gateway finalization should be started until the first slice is stable.