from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from ..models.operator import (
    OperatorProfile, 
    OperatorProfileCreate, 
    OperatorProfileUpdate,
    ServingArea,
    SubLocation
)
from ..database import get_database
from ..routers.auth import get_current_user

router = APIRouter(prefix="/operators", tags=["Operators"])


@router.get("/{operator_id}")
async def get_operator_profile(operator_id: str):
    """Get operator profile by ID (public)"""
    db = await get_database()
    
    try:
        profile = await db.operator_profiles.find_one({"_id": ObjectId(operator_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operator ID"
        )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operator profile not found"
        )
    
    # Convert ObjectId to string
    profile["_id"] = str(profile["_id"])
    return profile


@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def create_operator_profile(
    profile: OperatorProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create operator profile"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can create operator profiles"
        )
    
    db = await get_database()
    
    # Check if profile already exists
    existing_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator profile already exists"
        )
    
    # Create profile
    profile_dict = profile.model_dump()
    profile_dict["user_id"] = str(current_user["_id"])
    profile_dict["serving_areas"] = []
    profile_dict["average_rating"] = 0.0
    profile_dict["total_reviews"] = 0
    
    from datetime import datetime
    profile_dict["created_at"] = datetime.utcnow()
    profile_dict["updated_at"] = datetime.utcnow()
    
    result = await db.operator_profiles.insert_one(profile_dict)
    
    return {
        "message": "Operator profile created successfully",
        "profile_id": str(result.inserted_id)
    }


@router.get("/profile/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get current operator's profile"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can access operator profiles"
        )
    
    db = await get_database()
    profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    profile["_id"] = str(profile["_id"])
    return profile


@router.put("/profile/me")
async def update_my_profile(
    profile_update: OperatorProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current operator's profile"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can update operator profiles"
        )
    
    db = await get_database()
    
    # Get update data (exclude None values)
    update_data = {k: v for k, v in profile_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    from datetime import datetime
    update_data["updated_at"] = datetime.utcnow()
    
    # Try to update existing profile
    result = await db.operator_profiles.update_one(
        {"user_id": str(current_user["_id"])},
        {"$set": update_data}
    )
    
    # If no profile exists, create one
    if result.matched_count == 0:
        # Create new profile with the update data
        new_profile = {
            "user_id": str(current_user["_id"]),
            "business_name": profile_update.business_name or "My Business",
            "description": profile_update.description or "",
            "contact_number": profile_update.contact_number or "",
            "alternate_contact": profile_update.alternate_contact,
            "years_of_experience": profile_update.years_of_experience,
            "specializations": profile_update.specializations or [],
            "serving_areas": [],
            "average_rating": 0.0,
            "total_reviews": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.operator_profiles.insert_one(new_profile)
        return {
            "message": "Operator profile created and updated successfully",
            "profile_id": str(result.inserted_id)
        }
    
    return {"message": "Profile updated successfully"}


@router.post("/profile/serving-areas")
async def add_serving_area(
    serving_area: ServingArea,
    current_user: dict = Depends(get_current_user)
):
    """Add a new serving area"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can add serving areas"
        )
    
    for sub in serving_area.sub_locations:
        if not sub.coordinates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each sub-location must include coordinates"
            )

    db = await get_database()
    
    from datetime import datetime
    result = await db.operator_profiles.update_one(
        {"user_id": str(current_user["_id"])},
        {
            "$push": {"serving_areas": serving_area.model_dump()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area added successfully"}


@router.put("/profile/serving-areas/{area_index}")
async def update_serving_area(
    area_index: int,
    serving_area: ServingArea,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing serving area by index"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can update serving areas"
        )
    
    # Validate coordinates for all sub-locations
    for sub in serving_area.sub_locations:
        if not sub.coordinates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each sub-location must include coordinates"
            )

    db = await get_database()
    
    # Get current profile to verify area exists
    profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    if area_index < 0 or area_index >= len(profile.get("serving_areas", [])):
        raise HTTPException(status_code=404, detail="Serving area not found")
    
    from datetime import datetime
    
    # Update the specific serving area at the given index
    result = await db.operator_profiles.update_one(
        {"user_id": str(current_user["_id"])},
        {
            "$set": {
                f"serving_areas.{area_index}": serving_area.model_dump(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area updated successfully"}


@router.delete("/profile/serving-areas/{area_index}")
async def delete_serving_area(
    area_index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a serving area by index"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can delete serving areas"
        )

    db = await get_database()
    
    # Get current profile to verify area exists
    profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    if area_index < 0 or area_index >= len(profile.get("serving_areas", [])):
        raise HTTPException(status_code=404, detail="Serving area not found")
    
    from datetime import datetime
    
    # Remove the serving area at the given index
    serving_areas = profile.get("serving_areas", [])
    serving_areas.pop(area_index)
    
    result = await db.operator_profiles.update_one(
        {"user_id": str(current_user["_id"])},
        {
            "$set": {
                "serving_areas": serving_areas,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area deleted successfully"}


@router.get("/{operator_id}")
async def get_operator_profile(operator_id: str):
    """Get operator profile by ID"""
    db = await get_database()
    
    try:
        profile = await db.operator_profiles.find_one({"_id": ObjectId(operator_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid operator ID")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    profile["_id"] = str(profile["_id"])
    return profile


@router.get("/search/location")
async def search_operators_by_location(
    area_name: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None
):
    """Search operators by location"""
    db = await get_database()
    
    # Build search query
    query = {}
    if area_name:
        query["serving_areas.area_name"] = {"$regex": area_name, "$options": "i"}
    if state:
        query["serving_areas.state"] = {"$regex": state, "$options": "i"}
    if country:
        query["serving_areas.country"] = {"$regex": country, "$options": "i"}
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one search parameter is required"
        )
    
    operators = []
    cursor = db.operator_profiles.find(query).sort("average_rating", -1)
    
    async for operator in cursor:
        operator["_id"] = str(operator["_id"])
        operators.append(operator)
    
    return {"operators": operators, "count": len(operators)}
