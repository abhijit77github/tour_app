"""Seed quote inbox demo rows for local operator UI validation.

Creates a small, idempotent set of quote requests so the operator quote inbox
has enough records to exercise backend cursor pagination across at least two
pages in local development.

Run:
  python -m backend.scripts.seed_quote_inbox_demo
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings


SEED_TAG_PREFIX = "operator-quote-inbox-demo-v1"
TARGET_OPERATOR_EMAIL = "operator1@tourapp.local"
QUOTE_COUNT = 12


def resolve_quote_count() -> int:
    raw_value = os.getenv("QUOTE_COUNT")
    if not raw_value:
        return QUOTE_COUNT
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("QUOTE_COUNT must be an integer") from exc
    if parsed < 1:
        raise RuntimeError("QUOTE_COUNT must be at least 1")
    return parsed


def resolve_responded_count(quote_count: int) -> int:
    raw_value = os.getenv("RESPONDED_COUNT")
    if not raw_value:
        return min(4, max(1, quote_count // 2))
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("RESPONDED_COUNT must be an integer") from exc
    if parsed < 0:
        raise RuntimeError("RESPONDED_COUNT must be 0 or greater")
    return min(parsed, quote_count)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


async def resolve_users_and_profile(db):
    operator_user = await db.users.find_one({"email": TARGET_OPERATOR_EMAIL})
    if not operator_user:
        raise RuntimeError(f"Demo operator user not found: {TARGET_OPERATOR_EMAIL}")

    operator_profile = await db.operator_profiles.find_one({"user_id": str(operator_user["_id"])})
    if not operator_profile:
        raise RuntimeError(f"Operator profile not found for: {TARGET_OPERATOR_EMAIL}")

    tourist_rows = await db.users.find({"user_type": "tourist"}).sort("email", 1).to_list(length=10)
    if len(tourist_rows) < 2:
        raise RuntimeError("At least two tourist users are required before seeding quote inbox demo rows")

    return operator_user, operator_profile, tourist_rows


def build_locations(operator_profile: dict, index: int) -> list[dict]:
    serving_areas = operator_profile.get("serving_areas") or []
    if not serving_areas:
        raise RuntimeError("Target operator profile has no serving areas to build quote locations from")

    area = serving_areas[index % len(serving_areas)]
    area_coordinates = area.get("coordinates") or {"latitude": 12.9716, "longitude": 77.5946}
    locations = [
        {
            "name": area.get("area_name") or "Demo destination",
            "state": area.get("state"),
            "country": area.get("country") or "India",
            "coordinates": {
                "latitude": area_coordinates.get("latitude", 12.9716),
                "longitude": area_coordinates.get("longitude", 77.5946),
            },
            "notes": f"Primary stop for demo quote {index + 1}",
        }
    ]

    sub_locations = area.get("sub_locations") or []
    if sub_locations:
      sub = sub_locations[index % len(sub_locations)]
      sub_coordinates = sub.get("coordinates") or area_coordinates
      locations.append(
          {
              "name": sub.get("name") or f"Stop {index + 1}",
              "state": area.get("state"),
              "country": area.get("country") or "India",
              "coordinates": {
                  "latitude": sub_coordinates.get("latitude", area_coordinates.get("latitude", 12.9716)),
                  "longitude": sub_coordinates.get("longitude", area_coordinates.get("longitude", 77.5946)),
              },
              "notes": sub.get("description") or "Secondary stop for quote demo",
          }
      )

    return locations


def build_responses(operator_profile: dict, operator_user: dict, index: int, created_at: datetime, responded_count: int) -> list[dict]:
    if index >= responded_count:
        return []

    return [
        {
            "operator_id": str(operator_profile["_id"]),
            "operator_user_id": str(operator_user["_id"]),
            "operator_name": operator_profile.get("business_name"),
            "amount": 18000 + (index * 1250),
            "message": f"Demo response {index + 1}: curated local package with transport and guide options.",
            "created_at": created_at + timedelta(hours=2),
        }
    ]


def build_travel_window(index: int) -> tuple[str, datetime]:
    start_day = (index % 9) + 10
    end_day = start_day + 2
    travel_window = f"2026-07-{start_day:02d} to 2026-07-{end_day:02d}"
    travel_start_date = datetime(2026, 7, start_day, tzinfo=timezone.utc)
    return travel_window, travel_start_date


async def seed_quote_inbox_demo() -> None:
    client, db = await open_database()
    try:
        quote_count = resolve_quote_count()
        responded_count = resolve_responded_count(quote_count)
        operator_user, operator_profile, tourist_rows = await resolve_users_and_profile(db)
        await db.quote_requests.delete_many({"seed_tag": {"$regex": f"^{SEED_TAG_PREFIX}"}})

        now = utc_now()
        documents = []
        for index in range(quote_count):
            tourist = tourist_rows[index % len(tourist_rows)]
            created_at = now - timedelta(hours=index)
            responses = build_responses(operator_profile, operator_user, index, created_at, responded_count)
            travel_window, travel_start_date = build_travel_window(index)
            documents.append(
                {
                    "seed_tag": f"{SEED_TAG_PREFIX}-{index + 1}",
                    "tourist_id": str(tourist["_id"]),
                    "tourist_name": tourist.get("full_name"),
                    "locations": build_locations(operator_profile, index),
                    "notes": f"Demo quote request {index + 1} for inbox pagination validation.",
                    "preferences": "Comfortable pacing, local food options, and flexible pickup.",
                    "budget": 15000 + (index * 1000),
                    "travel_window": travel_window,
                    "travel_start_date": travel_start_date,
                    "travelers": 2 + (index % 4),
                    "status": "responded" if responses else "open",
                    "responses": responses,
                    "created_at": created_at,
                    "updated_at": responses[0]["created_at"] if responses else created_at,
                }
            )

        if documents:
            await db.quote_requests.insert_many(documents)

        responded = sum(1 for doc in documents if doc["responses"])
        print(f"Seeded {len(documents)} quote requests for {TARGET_OPERATOR_EMAIL}")
        print(f"Responded by target operator: {responded}")
        print(f"Seed tag prefix: {SEED_TAG_PREFIX}")
    finally:
        client.close()
        print("Closed MongoDB connection")


if __name__ == "__main__":
    asyncio.run(seed_quote_inbox_demo())