#!/usr/bin/env python3
"""
Migration script to initialize quote limits feature.

This script:
1. Adds membership_tier fields to existing users (defaults to "free")
2. Creates system_config collection with default quote limits
3. Creates necessary database indexes

Run from project root:
    python -m backend.scripts.init_quote_limits
"""

import asyncio
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.database import get_database, connect_to_mongo


async def migrate_user_membership_fields():
    """Add membership tier fields to existing users."""
    print("=" * 60)
    print("STEP 1: Migrating user membership fields")
    print("=" * 60)
    
    db = await get_database()
    
    # Count users without membership_tier field
    users_to_update = await db.users.count_documents({
        "membership_tier": {"$exists": False}
    })
    
    if users_to_update == 0:
        print("✓ All users already have membership_tier field")
        return
    
    print(f"Found {users_to_update} users to update...")
    
    # Update all users without membership_tier
    result = await db.users.update_many(
        {"membership_tier": {"$exists": False}},
        {
            "$set": {
                "membership_tier": "free",
                "membership_started_at": datetime.now(timezone.utc),
                "membership_expires_at": None
            }
        }
    )
    
    print(f"✓ Updated {result.modified_count} users with default 'free' membership")
    
    # Verify update
    total_users = await db.users.count_documents({})
    users_with_tier = await db.users.count_documents({
        "membership_tier": {"$exists": True}
    })
    
    print(f"✓ Verification: {users_with_tier}/{total_users} users now have membership_tier")


async def initialize_quote_limits_config():
    """Create system_config collection with default quote limits."""
    print("\n" + "=" * 60)
    print("STEP 2: Initializing quote limits configuration")
    print("=" * 60)
    
    db = await get_database()
    
    # Check if config already exists
    existing = await db.system_config.find_one({"config_key": "quote_limits"})
    
    if existing:
        print("✓ Quote limits config already exists:")
        print(f"  - Free tier: {existing.get('quote_limits', {}).get('free', 'N/A')} open requests")
        print(f"  - Premium tier: {existing.get('quote_limits', {}).get('premium', 'N/A')} open requests")
        print(f"  - Enterprise tier: {existing.get('quote_limits', {}).get('enterprise', 'N/A')} open requests")
        return
    
    # Create default config
    config_doc = {
        "config_key": "quote_limits",
        "quote_limits": {
            "free": 5,
            "premium": 20,
            "enterprise": 100
        },
        "updated_at": datetime.now(timezone.utc),
        "updated_by": None
    }
    
    await db.system_config.insert_one(config_doc)
    print("✓ Created quote limits configuration:")
    print(f"  - Free tier: 5 open requests")
    print(f"  - Premium tier: 20 open requests")
    print(f"  - Enterprise tier: 100 open requests")


async def create_database_indexes():
    """Create database indexes for performance."""
    print("\n" + "=" * 60)
    print("STEP 3: Creating database indexes")
    print("=" * 60)
    
    db = await get_database()
    
    # Index for users by membership_tier (for reporting)
    try:
        await db.users.create_index("membership_tier")
        print("✓ Created index on users.membership_tier")
    except Exception as e:
        print(f"⚠ Index on users.membership_tier: {str(e)}")
    
    # Index for users by membership_expires_at (for cleanup jobs)
    try:
        await db.users.create_index("membership_expires_at")
        print("✓ Created index on users.membership_expires_at")
    except Exception as e:
        print(f"⚠ Index on users.membership_expires_at: {str(e)}")
    
    # Compound index for counting open quotes per user
    try:
        await db.quote_requests.create_index([
            ("tourist_id", 1),
            ("status", 1)
        ])
        print("✓ Created compound index on quote_requests.(tourist_id, status)")
    except Exception as e:
        print(f"⚠ Index on quote_requests: {str(e)}")
    
    # Index for system_config by config_key
    try:
        await db.system_config.create_index("config_key", unique=True)
        print("✓ Created unique index on system_config.config_key")
    except Exception as e:
        print(f"⚠ Index on system_config.config_key: {str(e)}")


async def verify_migration():
    """Verify that migration completed successfully."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    db = await get_database()
    
    # Check users
    total_users = await db.users.count_documents({})
    users_with_tier = await db.users.count_documents({
        "membership_tier": {"$exists": True}
    })
    free_users = await db.users.count_documents({"membership_tier": "free"})
    premium_users = await db.users.count_documents({"membership_tier": "premium"})
    enterprise_users = await db.users.count_documents({"membership_tier": "enterprise"})
    
    print(f"✓ Users:")
    print(f"  - Total: {total_users}")
    print(f"  - With membership_tier: {users_with_tier}")
    print(f"  - Free: {free_users}")
    print(f"  - Premium: {premium_users}")
    print(f"  - Enterprise: {enterprise_users}")
    
    # Check config
    config = await db.system_config.find_one({"config_key": "quote_limits"})
    if config:
        print(f"\n✓ System Config:")
        print(f"  - Quote limits configured: Yes")
        print(f"  - Free limit: {config.get('quote_limits', {}).get('free')}")
        print(f"  - Premium limit: {config.get('quote_limits', {}).get('premium')}")
        print(f"  - Enterprise limit: {config.get('quote_limits', {}).get('enterprise')}")
    else:
        print(f"\n✗ System Config: NOT FOUND")
        return False
    
    # Check indexes
    user_indexes = await db.users.list_indexes().to_list(length=100)
    quote_indexes = await db.quote_requests.list_indexes().to_list(length=100)
    config_indexes = await db.system_config.list_indexes().to_list(length=100)
    
    print(f"\n✓ Indexes:")
    print(f"  - users: {len(user_indexes)} indexes")
    print(f"  - quote_requests: {len(quote_indexes)} indexes")
    print(f"  - system_config: {len(config_indexes)} indexes")
    
    return True


async def main():
    """Run all migration steps."""
    print("\n" + "=" * 60)
    print("QUOTE LIMITS FEATURE MIGRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Connect to MongoDB first
    await connect_to_mongo()
    
    try:
        # Step 1: Migrate user fields
        await migrate_user_membership_fields()
        
        # Step 2: Initialize config
        await initialize_quote_limits_config()
        
        # Step 3: Create indexes
        await create_database_indexes()
        
        # Verify everything
        success = await verify_migration()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ MIGRATION COMPLETED SUCCESSFULLY")
        else:
            print("✗ MIGRATION COMPLETED WITH WARNINGS")
        print("=" * 60)
        print(f"Finished at: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ MIGRATION FAILED")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print("=" * 60 + "\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
