# Operator Quote Requests Alignment Plan

## Problem Summary

The operator quote workflow is currently split across three surfaces:

- `/operator/home` recent quote preview
- `/operator/dashboard` quote tab
- `/operator/quotes` main inbox

These surfaces use the same backend inbox data but present it inconsistently. The current gaps are:

1. Different status semantics across views.
2. Different date, travel window, traveler, and budget formatting.
3. Home and Dashboard deep-link with `quoteId`, but the main inbox does not reliably focus that request.
4. Dashboard duplicates part of the response workflow instead of treating the main inbox as the canonical response surface.
5. The main inbox search and filter behavior is still page-local instead of dataset-wide.

## Immediate Action Plan

### P0 - Workflow Alignment

1. Make `/operator/quotes` the canonical quote review and response surface.
2. Normalize quote status, age, travel window, traveler, and budget formatting across Home, Dashboard, and Inbox.
3. Support `quoteId`-based focus in `/operator/quotes` so preview surfaces can take operators directly to the intended request.

### P1 - Queue Usability

1. Replace page-local search/filter with backend-backed query parameters.
2. Add queue sort modes in phases:
	- P1A: newest, unresponded first, highest budget.
	- P1D: travel soonest after a normalized travel-start field is added server-side.
3. Add urgency states in phases:
	- P1C: new, stale, responded recently.
	- P1D: travel soon after travel-date normalization is available.
4. Add server-backed secondary filters after sorting is stable:
	- location
	- budget band
	- travel window

### P2 - Daily-Use Efficiency

1. Add split-pane queue/detail view.
2. Add saved response drafts and reusable response templates.
3. Add compact list mode for high-volume operators.

### P3 - Scale and Governance

1. Scope inbox results to operator-relevant locations and permission boundaries.
2. Add idempotent response submission and duplicate-submit protection.
3. Add audit-friendly response metadata and operational reporting.

## Current Phase Implementation

This phase now extends beyond P0 and into the first P2 workspace slice:

1. Shared quote presentation helpers for Home, Dashboard, and Inbox.
2. Operator quote detail API for deep-link resolution.
3. Inbox focus behavior for `quoteId` routes.
4. Home and Dashboard preview alignment around the canonical inbox flow.
5. Dashboard quote tab reduced to a preview-only handoff surface so responses stay centralized in `/operator/quotes`.
6. Split-pane inbox workspace with a compact queue for triage and a persistent detail pane for review and response handoff.
7. Deliberate queue-density toggle so high-volume operators can switch between comfortable and compact triage modes without changing the detail pane.

## Status

- P0 completed and browser-validated with seeded operator quote requests.
- Dashboard handoff cleanup completed as the next phase slice after P0.
- P1A completed: inbox search and status filters are server-backed.
- P1B completed: inbox sort modes now support newest, unresponded first, and highest budget.
- P1C completed: inbox urgency badges now cover new, stale, and responded recently states.
- P1D completed: quote writes now persist `travel_start_date`, legacy rows fall back to parsed `travel_window`, and the inbox now supports travel-soonest sorting plus travel-soon urgency.
- P1E completed: the inbox now supports server-backed location, budget-band, and travel-window filters with dynamic filter options sourced from real quote data.
- P2A completed: `/operator/quotes` now uses a split-pane queue/detail review workspace on top of the stabilized filter and sort contract.
- P2B completed: the split-pane queue now supports a persistent compact-density toggle for high-volume operator triage.

## Current Delivery Sequence

1. P0: canonical inbox alignment across Home, Dashboard, and Inbox. Completed.
2. P1A: server-backed search and status filtering. Completed.
3. P1B: server-backed sort modes for daily queue triage. Completed.
4. P1C: urgency states and badges for stale and recently responded quotes. Completed.
5. P1D: travel-date normalization to unlock travel-soonest sorting and urgency. Completed.
6. P1E: richer server-backed filters for location, budget band, and travel window. Completed.
7. P2A: split-pane queue/detail review workspace. Completed.
8. P2B: compact-density queue toggle for high-volume operators. Completed.