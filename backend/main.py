import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone
from pathlib import Path
from .config import settings
from .database import connect_to_mongo, close_mongo_connection, get_backup_database, get_database
from .models.billing import DEFAULT_BILLING_PLANS
from .models.promotion_package import DEFAULT_PROMOTION_PACKAGES
from .routers import auth, operators, bookings, upload, chat, recommendations, quotes, admin, admin_backups, admin_billing, admin_notifications, user_notifications, tour_planner, operator_billing, operator_promotions, itineraries, access_control, tickets, admin_config
from .utils.notification_delivery import notification_worker_loop
from .utils.authorization import sync_system_roles
from .utils.backup_manager import BACKUP_TASKS_STATE_KEY, ensure_backup_directories, reconcile_orphaned_jobs

# Create FastAPI app
app = FastAPI(
    title="Tour App API",
    description="API for Tour Operator and Tourist Management System",
    version="1.0.0",
    debug=settings.debug
)

# Mount static files for uploads
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Connect to MongoDB on startup and setup indexes"""
    await connect_to_mongo()
    ensure_backup_directories()
    
    # Create TTL index for chat messages (7 days retention)
    db = await get_database()
    backup_db = await get_backup_database()
    try:
        # Create TTL index to auto-delete messages after 7 days (604800 seconds)
        await db.chat_messages.create_index(
            "created_at",
            expireAfterSeconds=604800  # 7 days = 7 * 24 * 60 * 60
        )
        await db.chat_messages.create_index([("sender_id", 1), ("receiver_id", 1), ("timestamp", -1)])
        await db.chat_messages.create_index([("receiver_id", 1), ("read", 1), ("timestamp", -1)])
        print("✅ Chat message TTL index created (7-day retention)")
    except Exception as e:
        print(f"⚠️ TTL index may already exist or error occurred: {e}")

    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index([("user_type", 1), ("created_at", -1)])
        await db.users.create_index([("user_type", 1), ("is_active", 1), ("created_at", -1), ("_id", -1)])
        await db.users.create_index([("user_type", 1), ("created_at", -1), ("_id", -1)])
        await db.users.create_index("membership_tier")  # For membership tier reporting
        await db.users.create_index("membership_expires_at")  # For cleanup jobs
        await db.admins.create_index("email", unique=True)
        await db.admins.create_index([("last_login", -1)])
        print("✅ User and admin indexes ensured")
    except Exception as e:
        print(f"⚠️ User/admin index setup may already exist or error occurred: {e}")

    try:
        await db.bookings.create_index([("tourist_id", 1), ("created_at", -1)])
        await db.bookings.create_index([("operator_id", 1), ("created_at", -1)])
        await db.bookings.create_index([("updated_at", -1)])
        await db.bookings.create_index([("booking_status.status", 1), ("updated_at", -1)])
        await db.bookings.create_index([("booking_status.status", 1), ("created_at", -1)])
        await db.ratings.create_index("booking_id", unique=True)
        await db.ratings.create_index([("operator_id", 1), ("created_at", -1)])
        await db.operator_profiles.create_index("user_id", unique=True)
        await db.quote_requests.create_index([("tourist_id", 1), ("created_at", -1)])
        await db.quote_requests.create_index([("updated_at", -1)])
        await db.quote_requests.create_index([("status", 1), ("created_at", -1)])
        await db.quote_requests.create_index([("created_at", -1), ("_id", -1)])
        await db.quote_requests.create_index([("status", 1), ("created_at", -1), ("_id", -1)])
        await db.quote_requests.create_index([("tourist_id", 1), ("status", 1)])  # For counting open quotes per user
        await db.quote_requests.create_index([("responses.operator_id", 1), ("created_at", -1)])
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("updated_at", -1), ("_id", -1)])
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("status", 1), ("updated_at", -1), ("_id", -1)])
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("budget_band", 1), ("updated_at", -1), ("_id", -1)])
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("duration_days", 1), ("updated_at", -1), ("_id", -1)])
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("trip_styles", 1), ("updated_at", -1), ("_id", -1)])
        await db.operator_itinerary_templates.create_index([
            ("operator_profile_id", 1),
            ("primary_location.area_name", 1),
            ("primary_location.state", 1),
            ("primary_location.country", 1),
            ("updated_at", -1),
            ("_id", -1),
        ])
        await db.operator_itinerary_templates.create_index(
            [
                ("operator_profile_id", 1),
                ("title", "text"),
                ("summary", "text"),
                ("notes_for_planner", "text"),
                ("primary_location.area_name", "text"),
                ("trip_styles", "text"),
                ("traveler_types", "text"),
            ],
            name="operator_itinerary_template_text_search",
            default_language="english",
            weights={
                "title": 10,
                "primary_location.area_name": 6,
                "trip_styles": 4,
                "summary": 3,
                "traveler_types": 2,
                "notes_for_planner": 1,
            },
        )
        print("✅ Booking, rating, and quote indexes ensured")
    except Exception as e:
        print(f"⚠️ Booking/rating/quote index setup may already exist or error occurred: {e}")

    try:
        await db.organizations.create_index("slug", unique=True)
        await db.organizations.create_index([("organization_type", 1), ("status", 1)])
        await db.organization_memberships.create_index(
            [("organization_id", 1), ("principal_type", 1), ("principal_id", 1)],
            unique=True,
        )
        await db.organization_memberships.create_index([("principal_type", 1), ("principal_id", 1), ("membership_status", 1)])
        await db.access_roles.create_index([("organization_type", 1), ("key", 1)], unique=True)
        await sync_system_roles(db)
        print("✅ Access control indexes ensured")
    except Exception as e:
        print(f"⚠️ Access control index setup may already exist or error occurred: {e}")

    try:
        await db.system_config.create_index("config_key", unique=True)
        print("✅ System configuration indexes ensured")
    except Exception as e:
        print(f"⚠️ System config index setup may already exist or error occurred: {e}")

    try:
        await db.support_tickets.create_index([("created_at", -1), ("_id", -1)])
        await db.support_tickets.create_index([("status", 1), ("priority", 1), ("created_at", -1), ("_id", -1)])
        await db.support_tickets.create_index([("priority", 1), ("created_at", -1), ("_id", -1)])
        await db.location_promotions.create_index(
            [("status", 1), ("start_at", 1), ("end_at", 1)]
        )
        await db.location_promotions.create_index(
            [
                ("normalized_location_scope.area_name", 1),
                ("normalized_location_scope.state", 1),
                ("normalized_location_scope.country", 1),
                ("service_type", 1),
            ]
        )
        await db.location_promotions.create_index("operator_profile_id")
        await db.promotion_events.create_index([("promotion_id", 1), ("created_at", -1)])
        print("✅ Location promotion indexes created")
    except Exception as e:
        print(f"⚠️ Location promotion indexes may already exist or error occurred: {e}")

    try:
        await db.promotion_packages.create_index("code", unique=True)
        await db.promotion_packages.create_index("is_active")
        await db.promotion_orders.create_index([("operator_profile_id", 1), ("created_at", -1)])
        await db.promotion_orders.create_index([("order_status", 1), ("payment_status", 1)])

        existing_codes = set(await db.promotion_packages.distinct("code"))
        default_rows = []
        now = datetime.now(timezone.utc)
        for package in DEFAULT_PROMOTION_PACKAGES:
            if package["code"] in existing_codes:
                continue
            default_rows.append({
                **package,
                "created_at": now,
                "updated_at": now,
            })

        if default_rows:
            await db.promotion_packages.insert_many(default_rows)
        print("✅ Promotion package indexes ensured")
    except Exception as e:
        print(f"⚠️ Promotion package setup may already exist or error occurred: {e}")

    try:
        await db.billing_plans.create_index("code", unique=True)
        await db.billing_plans.create_index("is_active")
        await db.provider_plans.create_index("operator_profile_id", unique=True)
        await db.provider_plans.create_index([("plan_status", 1), ("credits_remaining", 1)])
        await db.plan_orders.create_index("order_code", unique=True)
        await db.plan_orders.create_index([("operator_profile_id", 1), ("created_at", -1)])
        await db.plan_orders.create_index([("order_status", 1), ("payment_status", 1), ("created_at", -1)])
        await db.plan_orders.create_index([("operator_profile_id", 1), ("client_request_id", 1)])
        await db.credit_ledger.create_index([("operator_profile_id", 1), ("created_at", -1)])
        await db.billing_event_log.create_index("idempotency_key", unique=True)
        await db.billing_event_log.create_index([("operator_profile_id", 1), ("created_at", -1)])
        await db.billing_event_log.create_index([("promotion_id", 1), ("created_at", -1)])

        existing_plan_codes = set(await db.billing_plans.distinct("code"))
        default_plan_rows = []
        now = datetime.now(timezone.utc)
        for plan in DEFAULT_BILLING_PLANS:
            if plan["code"] in existing_plan_codes:
                continue
            default_plan_rows.append(
                {
                    **plan,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "system",
                }
            )

        if default_plan_rows:
            await db.billing_plans.insert_many(default_plan_rows)
        print("✅ Billing plan indexes ensured")
    except Exception as e:
        print(f"⚠️ Billing plan setup may already exist or error occurred: {e}")

    try:
        await db.admin_settings.create_index("key", unique=True)
        await db.admin_settings_history.create_index([("key", 1), ("changed_at", -1)])
        await db.admin_reports.create_index([("updated_at", -1)])
        await db.admin_report_schedules.create_index([("created_at", -1)])
        await db.admin_report_schedules.create_index([("status", 1), ("next_run", 1)])
        await db.admin_dashboards.create_index([("created_at", -1)])
        await db.audit_events.create_index([("category", 1), ("timestamp", -1)])
        await db.audit_events.create_index([("category", 1), ("event_type", 1), ("timestamp", -1)])
        await db.audit_events.create_index([("category", 1), ("severity", 1), ("timestamp", -1)])
        await db.audit_events.create_index([("category", 1), ("service", 1), ("timestamp", -1)])
        await db.audit_events.create_index([("metadata.principal_type", 1), ("metadata.email", 1), ("timestamp", -1)])
        print("✅ Admin settings indexes ensured")
    except Exception as e:
        print(f"⚠️ Admin settings index setup may already exist or error occurred: {e}")

    try:
        await db.notification_templates.create_index([("updated_at", -1)])
        await db.notification_campaigns.create_index([("created_at", -1)])
        await db.notification_campaigns.create_index([("status", 1), ("scheduled_for", 1)])
        await db.notification_audit_log.create_index([("entity_type", 1), ("entity_id", 1), ("created_at", -1)])
        await db.notification_deliveries.create_index([("campaign_id", 1), ("user_id", 1), ("channel", 1)], unique=True)
        await db.notification_deliveries.create_index([("user_id", 1), ("created_at", -1)])
        await db.notification_delivery_attempts.create_index([("campaign_id", 1), ("created_at", -1)])
        await db.notification_preferences.create_index("user_id", unique=True)
        await db.notification_worker_runs.create_index([("started_at", -1)])
        await db.admin_alerts.create_index([("read", 1), ("created_at", -1)])
        print("✅ Notification indexes ensured")
    except Exception as e:
        print(f"⚠️ Notification index setup may already exist or error occurred: {e}")

    try:
        await db.support_tickets.create_index([("organization_id", 1), ("created_at", -1)])
        await db.support_tickets.create_index([("status", 1), ("priority", 1), ("updated_at", -1)])
        await db.support_tickets.create_index([("requester_user_id", 1), ("created_at", -1)])
        print("✅ Support ticket indexes ensured")
    except Exception as e:
        print(f"⚠️ Support ticket index setup may already exist or error occurred: {e}")

    try:
        if settings.backup_metadata_database_name != settings.database_name:
            legacy_backup_count = await db.backup_jobs.count_documents({})
            backup_job_count = await backup_db.backup_jobs.count_documents({})
            if legacy_backup_count and not backup_job_count:
                legacy_jobs = await db.backup_jobs.find({}).to_list(length=None)
                if legacy_jobs:
                    await backup_db.backup_jobs.insert_many(legacy_jobs, ordered=False)
                    print(f"✅ Migrated {len(legacy_jobs)} backup jobs to ops database")
                    await db.drop_collection("backup_jobs")
                    print("✅ Removed legacy backup_jobs collection from primary database")
            elif legacy_backup_count and backup_job_count >= legacy_backup_count:
                await db.drop_collection("backup_jobs")
                print("✅ Removed duplicated legacy backup_jobs collection from primary database")

        await backup_db.backup_jobs.create_index("job_code", unique=True)
        await backup_db.backup_jobs.create_index([("job_type", 1), ("created_at", -1)])
        await backup_db.backup_jobs.create_index([("status", 1), ("updated_at", -1)])
        await backup_db.backup_jobs.create_index([("source_backup_id", 1), ("created_at", -1)])
        orphaned_jobs = await reconcile_orphaned_jobs(backup_db)
        if orphaned_jobs:
            print(f"✅ Reconciled {orphaned_jobs} orphaned backup jobs on startup")
        print("✅ Backup job indexes ensured")
    except Exception as e:
        print(f"⚠️ Backup job index setup may already exist or error occurred: {e}")

    try:
        await db.tourist_planner_quotas.create_index("user_id", unique=True)
        await db.tourist_planner_quota_ledger.create_index([("user_id", 1), ("created_at", -1)])
        await db.tourist_planner_reward_events.create_index("idempotency_key", unique=True)
        await db.tourist_planner_reward_verifications.create_index(
            [("user_id", 1), ("reward_id", 1), ("reward_type", 1)],
            unique=True,
        )
        print("✅ Planner quota indexes ensured")
    except Exception as e:
        print(f"⚠️ Planner quota index setup may already exist or error occurred: {e}")

    try:
        await db.operator_itinerary_templates.create_index([("operator_profile_id", 1), ("updated_at", -1)])
        await db.operator_itinerary_templates.create_index([("status", 1), ("primary_location.area_name", 1), ("duration_days", 1)])
        await db.tourist_itineraries.create_index([("tourist_id", 1), ("updated_at", -1)])
        print("✅ Itinerary indexes ensured")
    except Exception as e:
        print(f"⚠️ Itinerary index setup may already exist or error occurred: {e}")

    app.state.notification_worker_stop = asyncio.Event()
    setattr(app.state, BACKUP_TASKS_STATE_KEY, {})
    app.state.notification_worker_task = asyncio.create_task(
        notification_worker_loop(get_database, app.state.notification_worker_stop)
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    worker_stop = getattr(app.state, "notification_worker_stop", None)
    worker_task = getattr(app.state, "notification_worker_task", None)
    if worker_stop:
        worker_stop.set()
    if worker_task:
        try:
            await asyncio.wait_for(worker_task, timeout=5)
        except Exception:
            worker_task.cancel()
    await close_mongo_connection()


# Include routers
app.include_router(auth.router)
app.include_router(access_control.router)
app.include_router(operators.router)
app.include_router(bookings.router)
app.include_router(upload.router)
app.include_router(tour_planner.router)
app.include_router(chat.router)
app.include_router(recommendations.router)
app.include_router(quotes.router)
app.include_router(admin.router)
app.include_router(admin_backups.router)
app.include_router(admin_billing.router)
app.include_router(admin_notifications.router)
app.include_router(admin_config.router)
app.include_router(user_notifications.router)
app.include_router(operator_billing.router)
app.include_router(operator_promotions.router)
app.include_router(itineraries.router)
app.include_router(tickets.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Tour App API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
