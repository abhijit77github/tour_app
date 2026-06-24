"""Seed demo operators and offerings with images.

Run:
  python -m backend.scripts.seed_demo
"""

import asyncio
from datetime import datetime

from backend.config import settings
from backend.database import connect_to_mongo, get_database, close_mongo_connection
from backend.utils.auth import get_password_hash


OPERATORS = [
    {
        "email": "nina@wanderco.com",
        "full_name": "Nina Verma",
        "password": "Password123!",
        "user_type": "operator",
        "profile": {
            "business_name": "Himalayan Trails Co",
            "description": "Guided treks and scenic drives across Himachal with curated local stays.",
            "contact_number": "+91 98765 00001",
            "alternate_contact": None,
            "years_of_experience": 8,
            "specializations": ["Trekking", "Family", "Scenic Drives"],
            "service_types": ["tour", "car"],
            "car_services": [
                {
                    "vehicle_type": "SUV",
                    "vehicle_label": "Tempo Traveler",
                    "seats": 6,
                    "luggage_capacity": 500,
                    "pricing_model": "per_day",
                    "base_fare": 3500.0,
                    "fare_per_km": 8.0,
                    "operating_hours": "6AM-11PM",
                    "amenities": ["Air Conditioning", "WiFi", "Phone Charger"],
                    "coverage_areas": ["Manali", "Spiti", "Shimla", "Kinnaur"]
                },
                {
                    "vehicle_type": "Sedan",
                    "vehicle_label": "Toyota Innova",
                    "seats": 5,
                    "luggage_capacity": 300,
                    "pricing_model": "per_km",
                    "base_fare": 100.0,
                    "fare_per_km": 12.0,
                    "operating_hours": "24/7",
                    "amenities": ["Air Conditioning", "Phone Charger"],
                    "coverage_areas": ["Manali", "Shimla"]
                }
            ],
            "average_rating": 4.8,
            "total_reviews": 142,
            "serving_areas": [
                {
                    "area_name": "Manali",
                    "state": "Himachal Pradesh",
                    "country": "India",
                    "description": "Alpine getaways, riverside cafes, and day hikes.",
                    "images": [
                        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
                        "https://images.unsplash.com/photo-1477587458883-47145ed94245"
                    ],
                    "sub_locations": [
                        {
                            "name": "Solang Valley",
                            "description": "Cable car views and snow activities in winter.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1454496522488-7a8e488e8606"]
                        },
                        {
                            "name": "Old Manali",
                            "description": "Cafes, live music, and riverside walks.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1505761671935-60b3a7427bad"]
                        }
                    ],
                },
                {
                    "area_name": "Spiti",
                    "state": "Himachal Pradesh",
                    "country": "India",
                    "description": "High-altitude desert drives, monasteries, and starry skies.",
                    "images": [
                        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429"
                    ],
                    "sub_locations": [
                        {
                            "name": "Kaza",
                            "description": "Base town for Spiti with cafes and markets.",
                            "popular": False,
                            "images": []
                        },
                        {
                            "name": "Key Monastery",
                            "description": "Iconic hilltop monastery with sweeping valley views.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1469474968028-56623f02e42e"]
                        }
                    ],
                }
            ],
        },
    },
    {
        "email": "carlos@coastliners.com",
        "full_name": "Carlos D'Souza",
        "password": "Password123!",
        "user_type": "operator",
        "profile": {
            "business_name": "Coastliners Goa",
            "description": "Curated coastal experiences, kayak trails, and culinary walks.",
            "contact_number": "+91 98765 00002",
            "alternate_contact": None,
            "years_of_experience": 6,
            "specializations": ["Beaches", "Food Tours", "Water Sports"],
            "average_rating": 4.6,
            "total_reviews": 97,
            "serving_areas": [
                {
                    "area_name": "North Goa",
                    "state": "Goa",
                    "country": "India",
                    "description": "Beach clubs, forts, sunset cruises, and night markets.",
                    "images": [
                        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e",
                        "https://images.unsplash.com/photo-1505764706515-aa95265c5abc"
                    ],
                    "sub_locations": [
                        {
                            "name": "Chapora Fort",
                            "description": "Panoramic views and golden hour photography.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"]
                        },
                        {
                            "name": "Calangute Beach",
                            "description": "Watersports hub with vibrant shacks.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1493558103817-58b2924bce98"]
                        }
                    ],
                },
                {
                    "area_name": "South Goa",
                    "state": "Goa",
                    "country": "India",
                    "description": "Quieter beaches, backwater kayak routes, and spice farms.",
                    "images": ["https://images.unsplash.com/photo-1500375592092-40eb2168fd21"],
                    "sub_locations": [
                        {
                            "name": "Palolem",
                            "description": "Calm bay for kayaks and dolphin spotting.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1505761671935-60b3a7427bad"]
                        }
                    ],
                }
            ],
        },
    },
    {
        "email": "miho@urbanloop.jp",
        "full_name": "Miho Takeda",
        "password": "Password123!",
        "user_type": "operator",
        "profile": {
            "business_name": "Urban Loop Tokyo",
            "description": "Design-forward city walks, izakaya hops, and hidden galleries.",
            "contact_number": "+81 80-1234-5678",
            "alternate_contact": None,
            "years_of_experience": 5,
            "specializations": ["City Walks", "Food", "Art & Culture"],
            "average_rating": 4.9,
            "total_reviews": 188,
            "serving_areas": [
                {
                    "area_name": "Shibuya",
                    "state": "Tokyo",
                    "country": "Japan",
                    "description": "Neon crossings, record bars, third-wave coffee, and boutiques.",
                    "images": [
                        "https://images.unsplash.com/photo-1505761671935-60b3a7427bad",
                        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"
                    ],
                    "sub_locations": [
                        {
                            "name": "Cat Street",
                            "description": "Indie fashion lanes and cafes.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1521412644187-c49fa049e84d"]
                        },
                        {
                            "name": "Nonbei Yokocho",
                            "description": "Tiny izakaya alley with vintage charm.",
                            "popular": False,
                            "images": ["https://images.unsplash.com/photo-1505761671935-60b3a7427bad"]
                        }
                    ],
                },
                {
                    "area_name": "Asakusa",
                    "state": "Tokyo",
                    "country": "Japan",
                    "description": "Historic temples, river walks, and crafts workshops.",
                    "images": ["https://images.unsplash.com/photo-1499346030926-9a72daac6c63"],
                    "sub_locations": [
                        {
                            "name": "Senso-ji",
                            "description": "Iconic temple and Nakamise shopping street.",
                            "popular": True,
                            "images": ["https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"]
                        }
                    ],
                }
            ],
        },
    },
]


async def upsert_user(db, user_entry):
    existing = await db.users.find_one({"email": user_entry["email"]})
    if existing:
        return str(existing["_id"])

    now = datetime.utcnow()
    doc = {
        "email": user_entry["email"],
        "full_name": user_entry["full_name"],
        "user_type": user_entry["user_type"],
        "hashed_password": get_password_hash(user_entry["password"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    return str(result.inserted_id)


async def upsert_operator_profile(db, user_id: str, profile_data: dict):
    now = datetime.utcnow()
    existing = await db.operator_profiles.find_one({"user_id": user_id})

    base_profile = {
        "user_id": user_id,
        "business_name": profile_data.get("business_name"),
        "description": profile_data.get("description", ""),
        "profile_image": None,
        "contact_number": profile_data.get("contact_number", ""),
        "alternate_contact": profile_data.get("alternate_contact"),
        "years_of_experience": profile_data.get("years_of_experience"),
        "specializations": profile_data.get("specializations", []),
        "service_types": profile_data.get("service_types", ["tour"]),
        "car_services": profile_data.get("car_services", []),
        "serving_areas": profile_data.get("serving_areas", []),
        "average_rating": profile_data.get("average_rating", 0),
        "total_reviews": profile_data.get("total_reviews", 0),
        "created_at": now,
        "updated_at": now,
    }

    if existing:
        await db.operator_profiles.update_one(
            {"_id": existing["_id"]},
            {"$set": {**base_profile, "created_at": existing.get("created_at", now), "updated_at": now}}
        )
        return str(existing["_id"])

    result = await db.operator_profiles.insert_one(base_profile)
    return str(result.inserted_id)


async def seed():
    await connect_to_mongo()
    db = await get_database()

    for entry in OPERATORS:
        user_id = await upsert_user(db, entry)
        op_id = await upsert_operator_profile(db, user_id, entry["profile"])
        print(f"Seeded operator {entry['profile']['business_name']} (user_id={user_id}, operator_id={op_id})")

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(seed())
