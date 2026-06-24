# MongoDB Scaling Hardening

Last updated: June 16, 2026

## Purpose

This document records the current MongoDB scaling assessment for the Tour App codebase and a practical hardening plan for future growth.

It is not a generic MongoDB checklist. It is based on the current query patterns, document shapes, indexes, and backup flows used in this repository.

## Executive Verdict

MongoDB is a valid database choice for this application.

The current schema shape fits MongoDB well for:

- operator profiles with nested serving areas and car-service options
- quotes and bookings with flexible metadata
- notifications and chat payloads
- operational backup metadata stored separately in `tour_app_ops_db`

The limiting factor is not MongoDB itself. The limiting factor is the current application access pattern.

Current readiness:

- Good for small to medium production scale
- Not yet hardened for large admin datasets, large notification audiences, deep pagination, or high chat and rating volume
- Backup and restore are acceptable for small to medium data sizes, but not ideal for large production recovery objectives

## Implemented Hardening Status

Completed in the current codebase:

- Core hot-path indexes added for:
  - `users.email`, `users(user_type, created_at)`
  - `admins.email`, `admins(last_login)`
  - `bookings(tourist_id, created_at)`
  - `bookings(operator_id, created_at)`
  - `bookings(booking_status.status, updated_at)`
  - `ratings(booking_id)` unique
  - `ratings(operator_id, created_at)`
  - `quote_requests(tourist_id, created_at)`
  - `quote_requests(status, created_at)`
  - `chat_messages(sender_id, receiver_id, timestamp)`
  - `chat_messages(receiver_id, read, timestamp)`
- Rating summary recalculation moved from Python-side full scans to Mongo aggregation in the bookings flow.
- Notification audience preview, notification delivery listing, mark-all-read, and notification summary paths now use Mongo-side filtering or counting instead of broad in-memory scans.
- Admin financial transactions, commissions, payouts, and audit summary no longer load entire user and operator collections just to derive display data.
- Tour planner operator matching now performs a narrower Mongo prefilter plus field projection before Python ranking.
- Admin tourists, operators, and quotes screens now fetch one backend page at a time instead of loading 1000 rows into the browser and paginating client-side.
- Admin tourist quote counts and operator response counts are now batch-derived in Mongo per page instead of running per-row collection scans.
- Admin ticket and operator ticket queues now use cursor-based previous/next pagination on `created_at` and `_id` instead of deep offset scans or fixed bulk loads.
- Admin tourists, admin quotes, and admin operators now use cursor-based previous/next pagination on `created_at` and `_id` instead of offset-based paging.
- Admin performance and leaderboard endpoints now build enriched operator rows once and derive response counts and response times through a single Mongo aggregation instead of rescanning all quotes for every operator.
- Financial overview now computes revenue, monthly revenue, and pending payout totals with Mongo aggregation instead of materializing all completed and pending bookings in Python.
- Audit summary now limits booking and quote reads to the fields the feed uses, derives quote response counts in projection, and computes booking/quote security indicators with Mongo-side counts instead of Python loops over fetched documents.
- Reports summary now reads only the fields used by the reports, scheduling, and dashboards tabs, and the persisted report metadata collections have matching sort and status indexes for those views.
- Mongo client pooling and timeout behavior are now explicit in backend settings instead of relying on Motor defaults.

Still pending from the broader hardening roadmap:

- keyset or cursor pagination for the remaining deepest list paths and for large-offset workloads that still rely on `skip`
- deeper reporting redesign for the heaviest admin analytics endpoints
- larger-scale backup strategy beyond full logical dump and restore
- production calibration of the new pool/timeouts based on real traffic and observed saturation

## What Already Works Well

### Good document fit

- `backend/models/operator.py` stores operator profile data in a shape MongoDB can represent naturally.
- Flexible data domains such as quotes, recommendations, notifications, and backup jobs are reasonable fits for document storage.

### Startup index discipline exists

The application already creates indexes for several important domains in `backend/main.py`, including:

- access control collections
- promotions and promotion events
- billing and credit ledgers
- admin settings history
- notifications and deliveries
- support tickets
- backup jobs in the dedicated ops database
- itinerary-related collections

This is a good base. The problem is that several high-traffic collections still rely on implicit or missing index coverage.

### Operational separation for backup metadata

Backup job metadata now lives in a separate Mongo database via `BACKUP_METADATA_DATABASE_NAME`, which is the right operational boundary for destructive restores.

## Current Scaling Risks

Risks are ordered by impact.

### 1. Full collection reads in admin and notification flows

Several endpoints materialize whole collections or large slices into memory and then compute results in Python.

Examples:

- `backend/routers/admin.py`
  - `/financial/transactions` loads all users and all operator profiles, then iterates all bookings
  - `/financial/commissions` loads all operator profiles, then iterates bookings
  - `/financial/payouts` loads all operator profiles, then iterates bookings
  - `/audit/summary` loads all users and admins and recent bookings and quotes
- `backend/utils/notifications.py`
  - `list_matching_notification_recipients` loads up to 5000 users and filters in Python
  - `list_notification_deliveries` loads deliveries broadly and filters in memory
  - `mark_all_user_notifications_as_read` loads up to 2000 deliveries before filtering

Why it matters:

- memory usage grows with collection size
- response time becomes proportional to total collection size instead of filtered result size
- admin endpoints become fragile first, even if end-user flows are still fine

### 2. Ratings recalculate by scanning all operator ratings

`backend/routers/bookings.py` recalculates `average_rating` and `total_reviews` by reading all ratings for the operator after each create or update.

Why it matters:

- this makes each rating write costlier as history grows
- a popular operator with many reviews turns a simple write into an O(n) scan
- this will eventually impact both write latency and background load

### 3. Tour planner loads a large pool of operators and ranks in Python

`backend/routers/tour_planner.py` currently loads up to 300 operator profiles and scores them in Python.

Why it matters:

- request cost grows with profile count and profile size
- `serving_areas` and nested `sub_locations` make each document heavier
- this creates a synchronous high-latency path under growth

### 4. Deep skip/limit pagination will degrade

Several list endpoints still use `skip(...).limit(...)` pagination internally.

Examples:

- `backend/routers/admin.py` for deep admin paging after the UI-side 1000-row fetches were removed
- `backend/routers/tickets.py`

Why it matters:

- page N requires MongoDB to walk and discard earlier rows
- deep admin pages become increasingly expensive
- this is acceptable early, but not ideal for large collections

### 5. Core query paths are not fully indexed yet

`backend/main.py` creates many useful indexes, but some important query patterns still need explicit support.

High-value candidates:

- `users`
  - unique email lookup
  - admin and tourist search or sort paths
- `admins`
  - unique email lookup
- `bookings`
  - `(tourist_id, created_at)`
  - `(operator_id, created_at)`
  - `(booking_status.status, updated_at)` for admin and financial views
- `ratings`
  - `(operator_id, created_at)`
  - unique `booking_id` if one rating per booking is enforced
- `quote_requests`
  - `(tourist_id, created_at)`
  - `(status, created_at)`
- `chat_messages`
  - conversation-serving indexes in addition to the TTL index

### 6. Chat retention is operationally simple but incomplete for scale

`backend/main.py` creates a TTL index for `chat_messages`, which is fine for retention control.

What is still missing:

- query-serving indexes for participant pairs and timestamp sorting
- a plan for very high message volume if chat becomes a core product path

### 7. Connection pooling is default-only

`backend/database.py` uses `AsyncIOMotorClient(settings.mongodb_url)` without explicit pool tuning.

Why it matters:

- the default pool is acceptable early
- under sustained concurrency, connection wait behavior should be tuned explicitly
- production deployments should make pool sizing intentional, not implicit

### 8. Backup and restore are logical full-database operations

`backend/utils/backup_manager.py` uses full `mongodump` and `mongorestore` archive workflows.

This is acceptable for:

- local development
- small production databases
- controlled operational recovery where data volume is still moderate

This becomes weaker when:

- the main database grows large
- the backup window matters
- the restore time objective becomes strict
- full logical dumps become too slow or too heavy to run regularly

## Current Mongo Suitability by Scale Band

### Small scale

MongoDB is a strong fit.

Examples:

- early production
- small operator network
- moderate quote and booking volume
- low to moderate admin reporting usage

### Medium scale

MongoDB is still a good fit, but only if the hardening tasks below are implemented.

At this point the main pressure points become:

- admin analytics
- notifications
- planner matching
- ratings aggregation
- pagination

### Large scale

MongoDB can still work, but this codebase needs architectural hardening first.

Without that hardening, the current implementation will degrade before MongoDB itself becomes the bottleneck.

## Hardening Checklist

### P0: Do before expecting sustained growth

1. Add explicit indexes for core hot paths

- `users.email` unique
- `admins.email` unique
- `bookings(tourist_id, created_at)`
- `bookings(operator_id, created_at)`
- `bookings(booking_status.status, updated_at)`
- `ratings(operator_id, created_at)`
- `ratings(booking_id)` unique if rating-per-booking is guaranteed
- `quote_requests(tourist_id, created_at)`
- `quote_requests(status, created_at)`
- chat conversation indexes matching actual fetch queries

2. Remove full collection materialization from admin and notification flows

- replace `find({}).to_list(None)` or large in-memory filters with targeted queries
- move summary math into aggregation pipelines where practical
- cap expensive admin endpoints by date range or filters by default

3. Replace rating recalculation scans

Options:

- maintain incremental counters on `operator_profiles`
- or compute with Mongo aggregation and store the result asynchronously

4. Keep backup metadata isolated in `tour_app_ops_db`

- this is already done
- do not move `backup_jobs` back into the main application database

### P1: Do before high data volume or heavy admin usage

1. Replace skip-based pagination with cursor or keyset pagination

Priority endpoints:

- admin user listing
- admin quote listing
- admin operator listing
- support ticket listing

2. Make planner matching Mongo-first, Python-second

- narrow candidate operators using indexed filters before loading documents
- only apply final ranking logic in Python on a much smaller candidate set

3. Reduce document over-fetching on operator profiles

- avoid loading full profile payloads where only business name, rating, or minimal serving area info is needed
- use projections consistently

4. Add explicit production connection settings

- `maxPoolSize`
- `minPoolSize`
- timeouts appropriate to deployment profile

### P2: Do before large-scale production or strict SLAs

1. Rework backup strategy for larger databases

Consider:

- replica set snapshots
- managed backup tooling such as MongoDB Atlas backup if moving to Atlas
- incremental or point-in-time recovery strategy instead of only full logical dumps

2. Separate analytics-style reads from transactional reads

Options:

- precomputed summary collections
- scheduled aggregation jobs
- replica reads for heavy reporting if infrastructure supports it

3. Revisit large nested operator documents if usage grows substantially

- keep nested documents where they help reads
- normalize only where repeated over-fetching becomes measurable
- especially review `serving_areas` and `sub_locations` if planner and search volume grows

## Recommended Next Actions for This Repository

If only a few things are done next, they should be these:

1. Add missing indexes for bookings, ratings, users, admins, quote requests, and chat query paths.
2. Refactor the notification recipient and delivery listing helpers to query Mongo more selectively.
3. Replace rating average recomputation with incremental counters or aggregation.
4. Replace skip pagination on the largest admin collections.
5. Keep `mongodump` and `mongorestore` for now, but treat them as a temporary operational strategy rather than the final large-scale backup architecture.

## Final Recommendation

Stay with MongoDB.

For this product, changing databases now would not solve the main scaling risks. The larger issue is query discipline, index coverage, pagination strategy, and moving expensive Python-side computations into more scalable patterns.

The right path is:

- keep MongoDB
- harden the current access patterns
- revisit backup strategy later as data size and recovery requirements grow
