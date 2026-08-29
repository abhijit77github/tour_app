# Tour App - Development Tracker

Last Updated: 2026-08-29  
Tracker Mode: Active  
Canonical Status Doc: docs/project/CURRENT_STATUS.md

## Current Baseline

- Backend unit/integration suite is green.
- Latest run: `.venv/bin/python -m unittest discover -s backend/tests`
- Result: `Ran 41 tests ... OK`
- RBAC implementation phases are complete and documented.
- Historical sprint/phase progress docs have been archived.

Primary RBAC reference:
- docs/security/RBAC_ENDPOINT_MATRIX_AND_PHASE_PLAN.md

Archive references:
- docs/archive/completed/sprints/
- docs/archive/completed/phases/

## Active Workstreams

### 1) Security Rollout (RBAC Runtime Enablement)
Status: IN_PROGRESS

- [ ] Enable `RBAC_AUDIT_DECISIONS=true` in staging and review events for 48 hours
- [ ] Enable `RBAC_STEP_UP_REQUIRED=true` for sensitive admin actions
- [x] Remove legacy permission fallback and enforce strict registry-only deny on unmapped protected routes
- [ ] Capture rollout notes and final env defaults

### 2) Repository Hygiene
Status: IN_PROGRESS

- [ ] Split current mixed working tree into clean commits by concern
- [ ] Tag release boundary for "RBAC baseline complete"
- [ ] Ensure archived docs are excluded from active docs navigation except index pointers

### 3) Frontend Planner Refinement Continuation
Status: IN_PROGRESS

- [ ] Validate TourPlanner end-to-end flows against latest backend access rules
- [ ] Remove stale frontend artifacts and ensure route/view consistency
- [ ] Re-run frontend build and smoke checks after final cleanup

## Prioritized Next Tasks (Execution Order)

1. Create clean commit slices:
   - backend RBAC/auth/audit changes
   - test framework/fake updates
   - docs archive + status updates
   - frontend refinement files
2. Run staging rollout with RBAC flags in sequence:
   - audit decisions
   - step-up
   - strict registry coverage verification
3. Add a short post-rollout report in docs/security with:
   - flag states
   - denied-unmapped trend
   - production readiness sign-off

## Decisions and Constraints

- Strict registry-only RBAC is now enforced for protected admin/operator surfaces.
- Treat docs/project/CURRENT_STATUS.md as status source of truth.

## Change Log

### 2026-08-29

- Added centralized RBAC policy registry and registry-first permission resolution.
- Added eager operator owner provisioning during onboarding.
- Added JWT role/org claims for user/admin tokens.
- Added optional step-up and authorization decision auditing controls.
- Stabilized planner/notification test modules and restored full backend suite green.
- Archived completed sprint/phase docs under docs/archive/completed.
- Replaced stale tracker content with current execution-oriented tracker.
