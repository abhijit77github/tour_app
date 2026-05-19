"""Seed local development data.

Creates demo tourists/admins and multiple operator profiles in an idempotent way.

Run:
  python -m backend.scripts.seed_local_dev
"""

import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from backend.database import connect_to_mongo, get_database, close_mongo_connection
from backend.utils.auth import get_password_hash


TEST_USERS = [
    {
        "email": "tourist1@tourapp.local",
        "full_name": "Aarav Sharma",
        "password": "Password123!",
        "user_type": "tourist",
        "phone": "+91-9000000001",
    },
    {
        "email": "tourist2@tourapp.local",
        "full_name": "Diya Patel",
        "password": "Password123!",
        "user_type": "tourist",
        "phone": "+91-9000000002",
    },
    {
        "email": "operator1@tourapp.local",
        "full_name": "Rohan Mehta",
        "password": "Password123!",
        "user_type": "operator",
        "phone": "+91-9000000003",
    },
    {
        "email": "operator2@tourapp.local",
        "full_name": "Naina Kapoor",
        "password": "Password123!",
        "user_type": "operator",
        "phone": "+91-9000000004",
    },
    {
        "email": "operator3@tourapp.local",
        "full_name": "Kabir Iqbal",
        "password": "Password123!",
        "user_type": "operator",
        "phone": "+91-9000000005",
    },
]


TEST_ADMINS = [
    {
        "email": "admin@tourapp.local",
        "full_name": "Local Admin",
        "password": "admin@123",
        "phone": "+91-9000000100",
        "role": "super_admin",
    },
    {
        "email": "moderator@tourapp.local",
        "full_name": "Local Moderator",
        "password": "moderator@123",
        "phone": "+91-9000000101",
        "role": "moderator",
    },
]


OPERATOR_PROFILES = [
    {
        "email": "operator1@tourapp.local",
        "business_name": "Local Demo Tours",
        "description": "Curated local experiences for dev/testing.",
        "contact_number": "+91-9000000999",
        "years_of_experience": 4,
        "specializations": ["City Tours", "Food Walks"],
        "average_rating": 4.5,
        "total_reviews": 10,
        "serving_areas": [
            {
                "area_name": "Bangalore",
                "state": "Karnataka",
                "country": "India",
                "description": "Urban tours and weekend escapes",
                "images": [],
                "coordinates": {"latitude": 12.9716, "longitude": 77.5946},
                "sub_locations": [
                    {
                        "name": "Cubbon Park",
                        "description": "Green heritage park in city center",
                        "coordinates": {"latitude": 12.9763, "longitude": 77.5929},
                        "images": [],
                        "popular": True,
                    },
                    {
                        "name": "Lalbagh",
                        "description": "Botanical garden with glass house",
                        "coordinates": {"latitude": 12.9507, "longitude": 77.5848},
                        "images": [],
                        "popular": True,
                    },
                ],
            },
            {
                "area_name": "Mysore",
                "state": "Karnataka",
                "country": "India",
                "description": "Palace city and heritage walks",
                "images": [],
                "coordinates": {"latitude": 12.2958, "longitude": 76.6394},
                "sub_locations": [
                    {
                        "name": "Mysore Palace",
                        "description": "Royal palace and evening illumination",
                        "coordinates": {"latitude": 12.3051, "longitude": 76.6551},
                        "images": [],
                        "popular": True,
                    }
                ],
            },
        ],
    },
    {
        "email": "operator2@tourapp.local",
        "business_name": "Himalayan Escape Co",
        "description": "Mountain-focused itineraries and scenic weekend circuits.",
        "contact_number": "+91-9000000998",
        "years_of_experience": 7,
        "specializations": ["Trekking", "Family Trips", "Road Trips"],
        "average_rating": 4.7,
        "total_reviews": 35,
        "serving_areas": [
            {
                "area_name": "Manali",
                "state": "Himachal Pradesh",
                "country": "India",
                "description": "Alpine adventures and local cafe trails",
                "images": [],
                "coordinates": {"latitude": 32.2432, "longitude": 77.1892},
                "sub_locations": [
                    {
                        "name": "Solang Valley",
                        "description": "Valley sports and ropeway experience",
                        "coordinates": {"latitude": 32.3168, "longitude": 77.1557},
                        "images": [],
                        "popular": True,
                    },
                    {
                        "name": "Old Manali",
                        "description": "Riverside cafes and relaxed evenings",
                        "coordinates": {"latitude": 32.2569, "longitude": 77.1820},
                        "images": [],
                        "popular": True,
                    },
                ],
            },
            {
                "area_name": "Kasol",
                "state": "Himachal Pradesh",
                "country": "India",
                "description": "Parvati valley base and short hikes",
                "images": [],
                "coordinates": {"latitude": 32.0096, "longitude": 77.3140},
                "sub_locations": [
                    {
                        "name": "Chalal Trail",
                        "description": "Easy trail through pine forest",
                        "coordinates": {"latitude": 32.0138, "longitude": 77.3201},
                        "images": [],
                        "popular": False,
                    }
                ],
            },
        ],
    },
    {
        "email": "operator3@tourapp.local",
        "business_name": "Coastal Trails Goa",
        "description": "Beach circuits, sunset points, and local food routes.",
        "contact_number": "+91-9000000997",
        "years_of_experience": 5,
        "specializations": ["Beaches", "Water Sports", "Food Tours"],
        "average_rating": 4.6,
        "total_reviews": 22,
        "serving_areas": [
            {
                "area_name": "North Goa",
                "state": "Goa",
                "country": "India",
                "description": "Fort views, beaches, and nightlife",
                "images": [],
                "coordinates": {"latitude": 15.4909, "longitude": 73.8278},
                "sub_locations": [
                    {
                        "name": "Chapora Fort",
                        "description": "Sunset viewpoint with coastline panorama",
                        "coordinates": {"latitude": 15.6012, "longitude": 73.7360},
                        "images": [],
                        "popular": True,
                    },
                    {
                        "name": "Calangute Beach",
                        "description": "Popular beach with activities",
                        "coordinates": {"latitude": 15.5439, "longitude": 73.7553},
                        "images": [],
                        "popular": True,
                    },
                ],
            },
            {
                "area_name": "South Goa",
                "state": "Goa",
                "country": "India",
                "description": "Relaxed beaches and scenic drives",
                "images": [],
                "coordinates": {"latitude": 15.1570, "longitude": 74.0240},
                "sub_locations": [
                    {
                        "name": "Palolem",
                        "description": "Calm crescent beach ideal for kayaking",
                        "coordinates": {"latitude": 15.0100, "longitude": 74.0232},
                        "images": [],
                        "popular": True,
                    }
                ],
            },
        ],
    },
]


async def upsert_user(db, user: dict) -> str:
    existing = await db.users.find_one({"email": user["email"]})
    now = datetime.now(timezone.utc)

    if existing:
        await db.users.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "full_name": user["full_name"],
                    "phone": user.get("phone"),
                    "user_type": user["user_type"],
                    "is_active": True,
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    doc = {
        "email": user["email"],
        "full_name": user["full_name"],
        "phone": user.get("phone"),
        "user_type": user["user_type"],
        "hashed_password": get_password_hash(user["password"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    return str(result.inserted_id)


async def upsert_admin(db, admin: dict) -> str:
    existing = await db.admins.find_one({"email": admin["email"]})
    now = datetime.now(timezone.utc)

    if existing:
        await db.admins.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "full_name": admin["full_name"],
                    "phone": admin.get("phone"),
                    "role": admin["role"],
                    "is_active": True,
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    doc = {
        "email": admin["email"],
        "full_name": admin["full_name"],
        "phone": admin.get("phone"),
        "role": admin["role"],
        "hashed_password": get_password_hash(admin["password"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }
    result = await db.admins.insert_one(doc)
    return str(result.inserted_id)


async def upsert_operator_profile(db, operator_user_id: str, profile_data: dict) -> str:
    now = datetime.now(timezone.utc)
    existing = await db.operator_profiles.find_one({"user_id": operator_user_id})

    profile_doc = {
        "user_id": operator_user_id,
        "business_name": profile_data["business_name"],
        "description": profile_data.get("description", ""),
        "contact_number": profile_data.get("contact_number", ""),
        "alternate_contact": None,
        "years_of_experience": profile_data.get("years_of_experience"),
        "specializations": profile_data.get("specializations", []),
        "serving_areas": profile_data.get("serving_areas", []),
        "average_rating": profile_data.get("average_rating", 0),
        "total_reviews": profile_data.get("total_reviews", 0),
        "created_at": now,
        "updated_at": now,
    }

    if existing:
        await db.operator_profiles.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    **profile_doc,
                    "created_at": existing.get("created_at", now),
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    result = await db.operator_profiles.insert_one(profile_doc)
    return str(result.inserted_id)


async def upsert_booking(db, booking_doc: dict) -> str:
    existing = await db.bookings.find_one({"seed_tag": booking_doc["seed_tag"]})
    now = datetime.now(timezone.utc)

    if existing:
        await db.bookings.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    **booking_doc,
                    "created_at": existing.get("created_at", now),
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    booking_doc["created_at"] = now
    booking_doc["updated_at"] = now
    result = await db.bookings.insert_one(booking_doc)
    return str(result.inserted_id)


async def upsert_rating(db, rating_doc: dict) -> str:
    existing = await db.ratings.find_one({"seed_tag": rating_doc["seed_tag"]})
    now = datetime.now(timezone.utc)

    if existing:
        await db.ratings.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    **rating_doc,
                    "created_at": existing.get("created_at", now),
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    rating_doc["created_at"] = now
    result = await db.ratings.insert_one(rating_doc)
    return str(result.inserted_id)


async def seed_bookings_and_ratings(db, tourist_ids: list[str], operator_profile_ids: list[str]) -> None:
    if not tourist_ids or not operator_profile_ids:
        return

    profiles = {}
    for pid in operator_profile_ids:
        profile = await db.operator_profiles.find_one({"_id": ObjectId(pid)})
        if profile:
            profiles[pid] = profile

    booking_specs = [
        ("seed-booking-1", tourist_ids[0], operator_profile_ids[0], "completed", 22000),
        ("seed-booking-2", tourist_ids[1], operator_profile_ids[1], "confirmed", 18000),
        ("seed-booking-3", tourist_ids[0], operator_profile_ids[2], "pending", 14000),
        ("seed-booking-4", tourist_ids[1], operator_profile_ids[0], "completed", 26000),
    ]

    created_bookings = []
    for seed_tag, tourist_id, operator_id, status, cost in booking_specs:
        profile = profiles.get(operator_id)
        if not profile:
            continue

        serving_areas = profile.get("serving_areas", [])
        if not serving_areas:
            continue

        area = serving_areas[0]
        sub_locations = area.get("sub_locations", [])
        cart_items = []
        for sub in sub_locations[:2]:
            cart_items.append(
                {
                    "sub_location_name": sub.get("name", "Location"),
                    "description": sub.get("description"),
                    "selected": True,
                }
            )

        booking_doc = {
            "seed_tag": seed_tag,
            "tourist_id": tourist_id,
            "operator_id": operator_id,
            "cart": {
                "area_name": area.get("area_name", "Area"),
                "state": area.get("state", "State"),
                "country": area.get("country", "India"),
                "items": cart_items,
            },
            "booking_status": {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            },
            "estimated_cost": float(cost),
            "final_cost": float(cost + 1500) if status == "completed" else None,
            "notes": "Seeded demo booking for local development",
        }

        booking_id = await upsert_booking(db, booking_doc)
        created_bookings.append((seed_tag, booking_id, tourist_id, operator_id, status))
        print(f"Booking ready: {seed_tag} id={booking_id} status={status}")

    rating_specs = [
        ("seed-rating-1", "seed-booking-1", 4.0, "Great coordination and smooth trip."),
        ("seed-rating-2", "seed-booking-4", 5.0, "Excellent guide and itinerary coverage."),
    ]

    for rating_tag, booking_tag, rating_value, review_text in rating_specs:
        booking_info = next((b for b in created_bookings if b[0] == booking_tag), None)
        if not booking_info:
            continue

        _, booking_id, tourist_id, operator_id, status = booking_info
        if status != "completed":
            continue

        rating_doc = {
            "seed_tag": rating_tag,
            "booking_id": booking_id,
            "tourist_id": tourist_id,
            "operator_id": operator_id,
            "rating": rating_value,
            "review": review_text,
            "categories": {
                "hospitality": rating_value,
                "value": max(1, rating_value - 0.5),
                "experience": rating_value,
            },
        }

        rating_id = await upsert_rating(db, rating_doc)
        print(f"Rating ready: {rating_tag} id={rating_id} value={rating_value}")

    # Refresh operator profile aggregate rating fields based on rating collection.
    for operator_id in operator_profile_ids:
        ratings = []
        async for item in db.ratings.find({"operator_id": operator_id}):
            ratings.append(float(item.get("rating", 0)))

        if ratings:
            avg_rating = round(sum(ratings) / len(ratings), 2)
            await db.operator_profiles.update_one(
                {"_id": ObjectId(operator_id)},
                {
                    "$set": {
                        "average_rating": avg_rating,
                        "total_reviews": len(ratings),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )


async def seed() -> None:
    await connect_to_mongo()
    db = await get_database()

    operator_user_ids = {}
    tourist_user_ids = []
    for user in TEST_USERS:
        user_id = await upsert_user(db, user)
        print(f"User ready: {user['email']} ({user['user_type']}) id={user_id}")
        if user["user_type"] == "operator":
            operator_user_ids[user["email"]] = user_id
        elif user["user_type"] == "tourist":
            tourist_user_ids.append(user_id)

    for admin in TEST_ADMINS:
        admin_id = await upsert_admin(db, admin)
        print(f"Admin ready: {admin['email']} ({admin['role']}) id={admin_id}")

    operator_profile_ids = []
    for profile in OPERATOR_PROFILES:
        email = profile["email"]
        operator_user_id = operator_user_ids.get(email)
        if not operator_user_id:
            continue

        profile_id = await upsert_operator_profile(db, operator_user_id, profile)
        operator_profile_ids.append(profile_id)
        print(f"Operator profile ready: {profile['business_name']} id={profile_id}")

    await seed_bookings_and_ratings(db, tourist_user_ids, operator_profile_ids)

    await close_mongo_connection()
    print("Local dev seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
