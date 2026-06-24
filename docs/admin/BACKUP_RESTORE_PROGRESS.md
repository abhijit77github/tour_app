# Backup And Restore Progress

## Goal

Provide a super-admin-only backup and restore capability directly from the admin console, starting with local archive storage and S3 object storage, while keeping the design extensible for future providers.

## Phase Status

- Phase 1: Foundation and access control - completed
- Phase 2: Local backup and local restore - completed in API and admin UI
- Phase 3: S3 backup and S3 restore - completed in API and admin UI
- Phase 4: Hardening and operations - pending

## Implemented In This Slice

- Super-admin-only backend router at `/admin/backups`
- Backup job metadata isolated in a dedicated Mongo database
- Capability endpoint to expose tool and storage readiness
- Backup job metadata persisted in `backup_jobs`
- Queued backup jobs for `local` and `s3`
- Queued restore jobs from `local` and `s3`
- Local archive download endpoint for completed local backups
- Admin console page at `/admin/backups`
- Admin dashboard and sidebar entry points for super admins only

## Current Runtime Requirements

- `mongodump` must be installed on the backend host for backup creation
- `mongorestore` must be installed on the backend host for restore execution
- `BACKUP_S3_BUCKET` must be configured to enable S3 backups
- AWS credentials must be available through environment variables or instance role

## Pending Hardening

- Move background execution from in-process tasks to a durable worker queue for multi-instance deployments
- Migrate existing `backup_jobs` history from the primary app database into the dedicated ops database if legacy records must be preserved
- Add retention policies and scheduled cleanup for local archives
- Add audit log events for every backup and restore transition
- Add stronger restore guardrails such as secondary approval or maintenance mode
- Add automated API tests for success and failure scenarios