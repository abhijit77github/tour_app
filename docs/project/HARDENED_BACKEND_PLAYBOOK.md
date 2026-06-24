# Hardened Backend Playbook

Last updated: June 16, 2026

## Purpose

This playbook captures the backend hardening patterns that worked in this repository so future performance and operational work can be implemented in one focused pass instead of through multiple cleanup cycles.

It is intended for admin-heavy read paths, operational flows, and any endpoint that is likely to degrade first as data size grows.

## Single-Pass Workflow

Use this sequence for each hardening slice.

1. Start from the live route, not a generic utility.
2. Identify the exact fields the UI or caller renders.
3. Measure the current access pattern and remove the largest waste first.
4. Add or align indexes in the same slice as the query change.
5. Validate the API payload first, then validate the live UI.
6. Record the query pattern and the accepted shape in docs or repo memory.

## Route Triage Rules

### 1. Reduce over-fetching first

If the UI uses a small subset of each document, project only those fields.

Apply this when you see:

- `find()` calls with no projection on admin collections
- helper functions that return full documents and the caller reads only a few properties
- browser views that render cards, badges, counts, names, dates, or statuses only

Recent repository example:

- reports summary was trimmed to only the fields consumed by the reports, scheduling, and dashboards tabs

### 2. Replace Python scans with Mongo counts or aggregation

If the endpoint loops through whole result sets to compute totals, move that work into Mongo.

Prefer:

- `count_documents()` for simple indicators
- aggregation pipelines for sums, grouped counts, averages, and response-time calculations
- one batch aggregation per page instead of per-row follow-up queries

Recent repository examples:

- financial overview revenue and payout totals moved to aggregation
- audit summary indicators moved from Python loops to Mongo counts
- operator performance response stats moved into a single grouped aggregation

### 3. Move admin lists to cursor pagination when numbered jumps are not required

For append-heavy admin tables, prefer previous and next pagination using a stable sort key.

Repository standard:

- sort by `created_at` then `_id`
- encode the cursor as base64 JSON
- apply matching compound indexes with the same key order

Use this for:

- admin management lists
- ticket queues
- operator dashboards with chronological ordering

### 4. Isolate destructive-operation metadata

If a workflow can delete or restore business data, store its control-plane metadata outside the affected database.

Repository standard:

- backup and restore job metadata lives in `tour_app_ops_db`
- restore-surviving state must never live only in `tour_app_db`

### 5. Make connection behavior explicit before load testing

Do not rely on client defaults once a path becomes important.

Set and review:

- max and min pool size
- server selection timeout
- connect timeout
- socket timeout
- wait queue timeout

This makes saturation behavior observable and tunable before production traffic forces it.

## Indexing Rules

Add indexes in the same slice as the query rewrite.

Check for these pairings:

- pagination key order matches the compound index order
- sort fields are indexed on collections used by dashboards and admin timelines
- status plus next-run or updated-at combinations are indexed when a view filters and sorts by both
- unique constraints are enforced where the business rule already assumes uniqueness

Do not stop at query cleanup if the rewritten path still depends on collection scans.

## Validation Rules

Close each hardening slice with both validation layers.

### API validation

- hit the exact endpoint with a real auth token
- confirm the payload shape, not just the HTTP status
- verify that optional fallback behavior still works when data is sparse

### Live UI validation

- open the actual admin or operator page that consumes the endpoint
- exercise the tab, modal, or pagination path affected by the change
- confirm that trimmed fields did not break rendering contracts

API-only validation is not enough for admin work in this repository. Several regressions in this codebase were contract mismatches that only showed up in the browser.

## Acceptance Checklist

Treat a hardening slice as complete only when all of these are true.

- the route no longer performs obvious full scans, deep skip paging, or N+1 follow-up queries for the changed path
- the new query shape has matching indexes
- the API response contract is unchanged unless an intentional contract change was part of the task
- the live UI path was exercised successfully
- operational state survives destructive flows when applicable
- the result is documented in the scaling log or a project note

## Common Failure Modes Seen Here

- metadata for backup jobs was originally stored in the restored database and disappeared after restore
- admin pages often hid expensive patterns because the browser cached large lists and paginated client-side
- backend payloads and frontend expectations drifted when one side renamed or reshaped fields
- fixing the query without the index left the route improved but still not production-safe

## Apply This Playbook Next

Use this playbook before working on:

- remaining deep-offset admin endpoints
- heavier reporting or analytics routes
- large notification audiences
- any new operational workflow that needs recovery-safe state