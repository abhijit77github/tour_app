"""
Script to add the first admin user to the database.
Run this from the backend directory: python scripts/create_admin.py
"""
import asyncio
from motor.motor_asyncio import AsyncClient
from passlib.context import CryptContext
from datetime import datetime, timezone

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_first_admin():
    """Create the first admin user in the database"""
    
    # Database connection
    client = AsyncClient("mongodb://localhost:27017")
    db = client.tour_app
    
    try:
        # Check if admin already exists
        existing_admin = await db.admins.find_one({})
        if existing_admin:
            print("❌ Admin user(s) already exist in database. Skipping creation.")
            return
        
        # Create admin user
        admin_data = {
            "email": "admin@tourapp.com",
            "full_name": "Admin User",
            "phone": "+91-0000000000",
            "hashed_password": pwd_context.hash("admin@123"),
            "role": "super_admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        }
        
        result = await db.admins.insert_one(admin_data)
        
        print("✅ Admin user created successfully!")
        print(f"   Email: admin@tourapp.com")
        print(f"   Password: admin@123")
        print(f"   Role: super_admin")
        print(f"   ID: {result.inserted_id}")
        print("\n⚠️  IMPORTANT: Change this password after first login!")
        
    finally:
        client.close()

async def create_moderator_admin():
    """Create a moderator admin user"""
    
    client = AsyncClient("mongodb://localhost:27017")
    db = client.tour_app
    
    try:
        # Create moderator
        moderator_data = {
            "email": "moderator@tourapp.com",
            "full_name": "Moderator User",
            "phone": "+91-0000000001",
            "hashed_password": pwd_context.hash("moderator@123"),
            "role": "moderator",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        }
        
        result = await db.admins.insert_one(moderator_data)
        
        print("✅ Moderator user created successfully!")
        print(f"   Email: moderator@tourapp.com")
        print(f"   Password: moderator@123")
        print(f"   Role: moderator")
        print(f"   ID: {result.inserted_id}")
        
    finally:
        client.close()

async def main():
    """Main function"""
    print("\n" + "="*50)
    print("   TOUR APP - ADMIN USER CREATION")
    print("="*50 + "\n")
    
    # Create super admin
    print("Creating super admin user...")
    await create_first_admin()
    
    print("\n" + "-"*50 + "\n")
    
    # Create moderator
    print("Creating moderator user...")
    await create_moderator_admin()
    
    print("\n" + "="*50)
    print("   Setup complete! You can now login to admin dashboard.")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
