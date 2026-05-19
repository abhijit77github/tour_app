# Tour App - To Implementation (Future Work)

**Purpose:** Track all remaining implementation work after current Phase 3 progress.  
**Last Updated:** May 18, 2026  
**Owner:** Product + Engineering

---

## 1. Current Baseline

### Completed (high level)
- Core backend/frontend platform is running locally with Docker Compose.
- Tourist/operator main journeys are implemented (auth, search, quote, booking, chat, ratings).
- Admin dashboard core modules are implemented and API-backed.
- Admin financial, audit, reports, and settings now have summary APIs.
- Initial write APIs exist for reports and settings (reports CRUD-lite, schedules, settings save, API key/webhook actions).

### Still Not Fully Production-Ready
- Several admin operations are still UI-triggered placeholders (maintenance jobs, backup execution, deep integrations).
- Audit records are derived/aggregated, not yet event-sourced from every admin mutation.
- Reports/financial data is partly synthetic/derived, not from a dedicated payment ledger.
- Automated tests and CI checks are not yet comprehensive for new admin APIs.

---

## 2. Priority Roadmap

## P0 - Must Do Next

### A. Operational Settings Actions (Backend Jobs)
- [ ] Add real endpoints for:
  - [ ] backup now
  - [ ] restore from snapshot
  - [ ] clear cache
  - [ ] cleanup temp files
  - [ ] archive logs
  - [ ] optimize DB
- [ ] Add server-side validation + role checks.
- [ ] Add job status model (`queued/running/success/failed`).

**Acceptance:** Every settings operation returns a persisted job ID and status is queryable.

### B. Admin Mutation Audit Trail
- [ ] Add centralized helper to record admin action events.
- [ ] Log for all write endpoints under `/admin/*`:
  - [ ] actor admin id/email
  - [ ] action name
  - [ ] target resource + id
  - [ ] timestamp
  - [ ] result status
- [ ] Refactor audit summary to read real audit collection first.

**Acceptance:** Any admin write action appears in audit logs within one refresh.

### C. Reports Module Hardening
- [ ] Add persistent storage for report templates and generated files metadata.
- [ ] Replace synthetic report size/data with generated artifact metadata.
- [ ] Add report status lifecycle (`draft/processing/completed/failed`).

**Acceptance:** Report listing survives restarts and reflects real generation status.

---

## P1 - Important Stabilization

### D. Financial Domain Normalization
- [ ] Add dedicated `transactions` collection.
- [ ] Add payout batch model and payout ledger.
- [ ] Track payment method from source event (not synthetic cycling).
- [ ] Reconcile booking amount vs settlement amount.

**Acceptance:** Financial dashboard is fully derived from immutable transaction records.

### E. Admin APIs Quality Layer
- [ ] Add pagination/sorting/filtering to new summary endpoints.
- [ ] Add strict request/response schemas for new write endpoints.
- [ ] Add consistent error envelope and codes.

**Acceptance:** API contracts are documented and stable across all admin modules.

### F. Frontend Reliability
- [ ] Replace remaining `alert()` flows with toast/notification pattern.
- [ ] Add optimistic updates where safe + rollback on failure.
- [ ] Add route-level loading skeletons for admin pages.

**Acceptance:** No blocking alert-based UX in admin workflows.

---

## P2 - Scale and Delivery

### G. Testing and CI
- [ ] Backend tests for all new admin write endpoints.
- [ ] Frontend integration tests for admin financial/audit/reports/settings.
- [ ] Docker Compose smoke test in CI pipeline.

**Acceptance:** CI gate includes unit + API + smoke tests.

### H. Security and Compliance
- [ ] Secrets hardening for production (`SECRET_KEY`, mail creds, DB auth).
- [ ] RBAC tightening per admin role (`super_admin/admin/moderator`).
- [ ] Add sensitive field redaction in logs and API responses.

**Acceptance:** Security review checklist passed for admin surfaces.

### I. Observability
- [ ] Structured logging for backend (request_id, actor_id, endpoint).
- [ ] Metrics for admin endpoints (latency/error rate).
- [ ] Health dashboard for DB/API/dependency status.

**Acceptance:** Top 5 admin paths are observable in logs/metrics.

---

## 3. Suggested Implementation Order (Execution)

1. P0-A operational jobs
2. P0-B centralized audit trail
3. P0-C reports lifecycle and persistence
4. P1-D financial normalization
5. P1-E API quality layer
6. P1-F frontend UX reliability
7. P2-G testing + CI
8. P2-H security hardening
9. P2-I observability

---

## 4. Data/Schema Additions (Proposed)

- `admin_audit_logs`
- `admin_jobs`
- `admin_reports` (already used, formalize schema)
- `admin_report_schedules` (already used, formalize schema)
- `admin_dashboards` (already used, formalize schema)
- `transactions`
- `payout_batches`
- `payout_items`

---

## 5. Open Questions

- Should report generation be synchronous or background-job based?
- Which payment provider will be source of truth for transactions?
- Do we need multi-tenant admin isolation in future?
- What is the required retention period for audit logs?

---

## 6. Definition of Done (Future)

- [ ] All admin write actions are persisted and auditable.
- [ ] All key admin pages are API-backed without mock-only logic.
- [ ] Financial data is ledger-based and reconcilable.
- [ ] Test coverage and CI are in place.
- [ ] Security and observability baselines are complete.
