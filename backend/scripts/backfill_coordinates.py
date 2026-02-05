"""Backfill coordinates for existing sub-locations.

This script adds GPS coordinates to sub-locations in serving areas.
Useful for testing the "View on Map" feature.

Run:
  python -m backend.scripts.backfill_coordinates
"""

import asyncio
from backend.database import connect_to_mongo, get_database, close_mongo_connection

# Real coordinates for known locations
COORDINATES_MAP = {
    # Manali, Himachal Pradesh, India
    "Solang Valley": {"latitude": 32.2433, "longitude": 77.1892},
    "Old Manali": {"latitude": 32.2389, "longitude": 77.1900},
    
    # Spiti, Himachal Pradesh, India
    "Kaza": {"latitude": 32.2245, "longitude": 78.0633},
    "Key Monastery": {"latitude": 32.1908, "longitude": 78.1631},
    
    # Goa, India
    "Chapora Fort": {"latitude": 15.5794, "longitude": 73.7471},
    "Calangute Beach": {"latitude": 15.6831, "longitude": 73.7650},
    "Palolem": {"latitude": 15.0094, "longitude": 73.9927},
    
    # Tokyo, Japan
    "Cat Street": {"latitude": 35.6625, "longitude": 139.7311},
    "Nonbei Yokocho": {"latitude": 35.6654, "longitude": 139.7417},
    "Senso-ji": {"latitude": 35.7148, "longitude": 139.7967},
}


async def backfill_coordinates():
    """Add coordinates to sub-locations that are missing them."""
    await connect_to_mongo()
    db = await get_database()

    try:
        # Get all operator profiles
        operators = await db.operator_profiles.find({}).to_list(None)
        
        if not operators:
            print("❌ No operators found in database. Please seed data first.")
            print("   Run: python -m backend.scripts.seed_demo")
            await close_mongo_connection()
            return

        print(f"Found {len(operators)} operator(s)")
        
        updated_count = 0
        total_sub_locations = 0

        for op in operators:
            print(f"\n📍 Operator: {op.get('business_name', 'Unknown')}")
            
            if "serving_areas" not in op:
                print("  ⚠️  No serving areas")
                continue
            
            for area_idx, area in enumerate(op["serving_areas"]):
                if "sub_locations" not in area:
                    continue
                
                area_name = area.get("area_name", "Unknown")
                print(f"  📌 Area: {area_name}")
                
                for sub_idx, sub in enumerate(area["sub_locations"]):
                    total_sub_locations += 1
                    sub_name = sub.get("name", f"Location {sub_idx}")
                    
                    # Check if coordinates already exist
                    if sub.get("coordinates"):
                        print(f"    ✅ {sub_name} - Already has coordinates")
                        continue
                    
                    # Look up coordinates
                    if sub_name in COORDINATES_MAP:
                        coords = COORDINATES_MAP[sub_name]
                        print(f"    📍 {sub_name} - Adding coordinates: {coords['latitude']}, {coords['longitude']}")
                        
                        # Update the sub-location with coordinates
                        await db.operator_profiles.update_one(
                            {"_id": op["_id"]},
                            {
                                "$set": {
                                    f"serving_areas.{area_idx}.sub_locations.{sub_idx}.coordinates": coords
                                }
                            }
                        )
                        updated_count += 1
                    else:
                        # Use fallback: approximate center of area
                        area_state = area.get("state", "")
                        area_country = area.get("country", "")
                        
                        if "Himachal Pradesh" in area_state:
                            fallback_coords = {"latitude": 32.0, "longitude": 77.5}
                        elif "Goa" in area_state:
                            fallback_coords = {"latitude": 15.3, "longitude": 73.9}
                        elif "Tokyo" in area_state or "Japan" in area_country:
                            fallback_coords = {"latitude": 35.6762, "longitude": 139.6503}
                        else:
                            fallback_coords = {"latitude": 20.5937, "longitude": 78.9629}  # India center
                        
                        print(f"    📍 {sub_name} - Using fallback: {fallback_coords['latitude']}, {fallback_coords['longitude']}")
                        
                        await db.operator_profiles.update_one(
                            {"_id": op["_id"]},
                            {
                                "$set": {
                                    f"serving_areas.{area_idx}.sub_locations.{sub_idx}.coordinates": fallback_coords
                                }
                            }
                        )
                        updated_count += 1

        print(f"\n✅ Done!")
        print(f"   Total sub-locations: {total_sub_locations}")
        print(f"   Updated: {updated_count}")
        
        if updated_count > 0:
            print(f"\n✨ All sub-locations now have coordinates for the 'View on Map' feature!")

    except Exception as e:
        print(f"❌ Error during backfill: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(backfill_coordinates())
