"""Create local-development admin accounts.

Run from the repository root:
  python -m backend.scripts.create_admin
"""

import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings
from backend.utils.auth import get_password_hash


ADMIN_USERS = [
    {
        "email": "admin@tourapp.local",
        "full_name": "Local Admin",
        "phone": "+91-9000000100",
        "password": "admin@123",
        "role": "super_admin",
    },
    {
        "email": "moderator@tourapp.local",
        "full_name": "Local Moderator",
        "phone": "+91-9000000101",
        "password": "moderator@123",
        "role": "moderator",
    },
]


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

    raise RuntimeError(
        f"Unable to connect to MongoDB using {candidate_urls} for database {settings.database_name}"
    ) from last_error


async def ensure_admin(db, admin_data):
    existing_admin = await db.admins.find_one({"email": admin_data["email"]})
    if existing_admin:
        print(f"ℹ️  Admin already exists: {admin_data['email']}")
        return False

    now = datetime.now(timezone.utc)
    doc = {
        "email": admin_data["email"],
        "full_name": admin_data["full_name"],
        "phone": admin_data["phone"],
        "hashed_password": get_password_hash(admin_data["password"]),
        "role": admin_data["role"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }

    result = await db.admins.insert_one(doc)
    print("✅ Admin user created successfully!")
    print(f"   Email: {admin_data['email']}")
    print(f"   Password: {admin_data['password']}")
    print(f"   Role: {admin_data['role']}")
    print(f"   ID: {result.inserted_id}")
    return True


async def main():
    print("\n" + "=" * 50)
    print("   TOUR APP - LOCAL ADMIN USER CREATION")
    print("=" * 50 + "\n")

    client, db = await open_database()
    try:
        print(f"Target database: {settings.database_name}\n")
        created_any = False
        for admin_data in ADMIN_USERS:
            print(f"Ensuring {admin_data['role']} account...")
            created = await ensure_admin(db, admin_data)
            created_any = created_any or created
            print()

        if created_any:
            print("⚠️  IMPORTANT: Change these passwords after first login!")
        else:
            print("No new admin accounts were created.")

        print("\n" + "=" * 50)
        print("   Local admin setup complete.")
        print("=" * 50 + "\n")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
