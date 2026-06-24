"""Seed operator billing activity for local UI validation.

Creates a small, tagged dataset for the existing operator1 demo account so the
operator billing analytics page has non-empty charts, hover states, and
surface toggles to exercise locally.

Run:
  python -m backend.scripts.seed_operator_billing_demo
"""

import asyncio
from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings
from backend.models.billing import DEFAULT_BILLING_PLANS
from backend.utils.billing import billing_cycle_window, build_billing_event_idempotency_key, utc_now


SEED_TAG = "operator-billing-ui-demo-v1"
TARGET_EMAIL = "operator1@tourapp.local"
TARGET_PLAN_CODE = "GROWTH"


EVENT_BLUEPRINTS = [
    {
        "days_ago": 6,
        "surface": "search",
        "event_type": "profile_click",
        "credits": 1,
        "amount": 32.0,
        "billable": True,
        "label": "Bengaluru heritage click",
    },
    {
        "days_ago": 5,
        "surface": "planner",
        "event_type": "qualified_lead",
        "credits": 2,
        "amount": 48.0,
        "billable": True,
        "label": "Planner shortlist handoff",
    },
    {
        "days_ago": 5,
        "surface": "planner",
        "event_type": "impression",
        "credits": 0,
        "amount": 0.0,
        "billable": False,
        "label": "Planner impression",
    },
    {
        "days_ago": 4,
        "surface": "search",
        "event_type": "profile_click",
        "credits": 1,
        "amount": 36.0,
        "billable": True,
        "label": "Mysore promoted click",
    },
    {
        "days_ago": 3,
        "surface": "planner",
        "event_type": "conversion",
        "credits": 3,
        "amount": 72.0,
        "billable": True,
        "label": "Template save conversion",
    },
    {
        "days_ago": 2,
        "surface": "quotes",
        "event_type": "qualified_lead",
        "credits": 2,
        "amount": 54.0,
        "billable": True,
        "label": "Quote unlock",
    },
    {
        "days_ago": 1,
        "surface": "search",
        "event_type": "profile_click",
        "credits": 1,
        "amount": 40.0,
        "billable": True,
        "label": "Weekend promoted click",
    },
]


async def ensure_growth_plan(db) -> dict:
    plan = await db.billing_plans.find_one({"code": TARGET_PLAN_CODE})
    if plan:
        return plan

    fallback = next(item for item in DEFAULT_BILLING_PLANS if item["code"] == TARGET_PLAN_CODE)
    document = dict(fallback)
    document["created_at"] = utc_now()
    document["updated_at"] = utc_now()
    await db.billing_plans.insert_one(document)
    return await db.billing_plans.find_one({"code": TARGET_PLAN_CODE})


async def resolve_target_operator(db) -> tuple[dict, dict]:
    user = await db.users.find_one({"email": TARGET_EMAIL})
    if not user:
        raise RuntimeError(f"Demo operator user not found: {TARGET_EMAIL}")

    profile = await db.operator_profiles.find_one({"user_id": str(user["_id"])})
    if not profile:
        raise RuntimeError(f"Operator profile not found for: {TARGET_EMAIL}")

    return user, profile


async def clear_previous_seed_rows(db, operator_profile_id: str) -> None:
    await db.billing_event_log.delete_many(
        {
            "operator_profile_id": operator_profile_id,
            "metadata.seed_tag": SEED_TAG,
        }
    )
    await db.credit_ledger.delete_many(
        {
            "operator_profile_id": operator_profile_id,
            "source_reference_type": "seed_demo_event",
            "notes": {"$regex": SEED_TAG},
        }
    )


async def open_database():
    candidate_urls = [settings.mongodb_url]
    if "mongo:27017" in settings.mongodb_url:
        candidate_urls.append(settings.mongodb_url.replace("mongo:27017", "localhost:27017"))
    elif settings.mongodb_url != "mongodb://localhost:27017":
        candidate_urls.append("mongodb://localhost:27017")

    last_error = None
    for url in dict.fromkeys(candidate_urls):
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=3000)
        try:
            await client.admin.command("ping")
            print(f"Connected to MongoDB at {url}")
            return client, client[settings.database_name]
        except Exception as exc:
            client.close()
            last_error = exc

    raise RuntimeError(f"Unable to connect to MongoDB using {candidate_urls}") from last_error


async def seed_operator_billing_demo() -> None:
    client, db = await open_database()
    try:
        user, profile = await resolve_target_operator(db)
        operator_profile_id = str(profile["_id"])
        operator_user_id = str(user["_id"])
        plan = await ensure_growth_plan(db)

        await clear_previous_seed_rows(db, operator_profile_id)

        total_billable_credits = sum(item["credits"] for item in EVENT_BLUEPRINTS if item["billable"])
        included_credits = int(plan.get("included_credits") or 250)
        credits_remaining = max(included_credits - total_billable_credits, 0)
        now = utc_now()
        cycle_start, cycle_end = billing_cycle_window(now)

        await db.provider_plans.update_one(
            {"operator_profile_id": operator_profile_id},
            {
                "$set": {
                    "operator_profile_id": operator_profile_id,
                    "operator_user_id": operator_user_id,
                    "plan_code": plan["code"],
                    "plan_name": plan["name"],
                    "plan_status": "active",
                    "included_credits": included_credits,
                    "credits_remaining": credits_remaining,
                    "billing_cycle_start_at": cycle_start,
                    "billing_cycle_end_at": cycle_end,
                    "auto_renew": False,
                    "updated_at": now,
                    "activated_at": now,
                    "last_assignment_notes": f"{SEED_TAG}: reset for local billing UI demo",
                    "last_assigned_by": "seed-script",
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

        balance = included_credits
        await db.credit_ledger.insert_one(
            {
                "operator_profile_id": operator_profile_id,
                "entry_type": "grant",
                "credits_delta": included_credits,
                "balance_after": balance,
                "source_surface": "admin",
                "source_reference_type": "seed_demo_event",
                "source_reference_id": f"{SEED_TAG}:grant",
                "notes": f"{SEED_TAG}: local demo credit grant",
                "created_at": now - timedelta(days=7),
                "created_by": "seed-script",
            }
        )

        inserted_events = 0
        for index, blueprint in enumerate(EVENT_BLUEPRINTS, start=1):
            created_at = now - timedelta(days=blueprint["days_ago"])
            source_reference_id = f"{SEED_TAG}:event:{index}"
            idempotency_key = build_billing_event_idempotency_key(
                source_surface=blueprint["surface"],
                event_type=blueprint["event_type"],
                operator_profile_id=operator_profile_id,
                source_reference_type="seed_demo_event",
                source_reference_id=source_reference_id,
                anonymous_session_id=None,
            )

            await db.billing_event_log.insert_one(
                {
                    "idempotency_key": idempotency_key,
                    "operator_profile_id": operator_profile_id,
                    "promotion_id": None,
                    "source_surface": blueprint["surface"],
                    "event_type": blueprint["event_type"],
                    "source_reference_type": "seed_demo_event",
                    "source_reference_id": source_reference_id,
                    "anonymous_session_id": None,
                    "request_fingerprint": None,
                    "credits_charged": blueprint["credits"] if blueprint["billable"] else 0,
                    "currency_amount": blueprint["amount"] if blueprint["billable"] else 0.0,
                    "is_billable": blueprint["billable"],
                    "outcome_reason": "charged" if blueprint["billable"] else "tracked_only",
                    "metadata": {
                        "seed_tag": SEED_TAG,
                        "seed_label": blueprint["label"],
                        "plan_code": plan["code"],
                    },
                    "created_at": created_at,
                }
            )
            inserted_events += 1

            if blueprint["billable"]:
                balance -= blueprint["credits"]
                await db.credit_ledger.insert_one(
                    {
                        "operator_profile_id": operator_profile_id,
                        "entry_type": "debit",
                        "credits_delta": -blueprint["credits"],
                        "balance_after": balance,
                        "source_surface": blueprint["surface"],
                        "source_reference_type": "seed_demo_event",
                        "source_reference_id": source_reference_id,
                        "notes": f"{SEED_TAG}: {blueprint['label']}",
                        "created_at": created_at,
                        "created_by": "seed-script",
                    }
                )

        print(f"Seeded {inserted_events} billing events for {TARGET_EMAIL}")
        print(f"Plan: {plan['code']} | Credits remaining: {credits_remaining}/{included_credits}")
        print(f"Seed tag: {SEED_TAG}")
    finally:
        client.close()
        print("Closed MongoDB connection")


if __name__ == "__main__":
    asyncio.run(seed_operator_billing_demo())