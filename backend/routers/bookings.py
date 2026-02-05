from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from bson import ObjectId
from ..models.booking import (
    Booking,
    BookingCreate,
    Rating,
    RatingCreate
)
from ..database import get_database
from ..routers.auth import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking: BookingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new booking"""
    if current_user["user_type"] != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tourists can create bookings"
        )
    
    db = await get_database()
    
    # Verify operator exists
    try:
        operator = await db.operator_profiles.find_one({"_id": ObjectId(booking.operator_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid operator ID")
    
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    # Create booking
    booking_dict = booking.model_dump()
    booking_dict["tourist_id"] = str(current_user["_id"])
    booking_dict["booking_status"] = {"status": "pending"}
    
    from datetime import datetime
    booking_dict["created_at"] = datetime.utcnow()
    booking_dict["updated_at"] = datetime.utcnow()
    
    result = await db.bookings.insert_one(booking_dict)
    
    return {
        "message": "Booking created successfully",
        "booking_id": str(result.inserted_id)
    }


@router.get("/my-bookings")
async def get_my_bookings(current_user: dict = Depends(get_current_user)):
    """Get all bookings for current user"""
    db = await get_database()
    
    if current_user["user_type"] == "tourist":
        query = {"tourist_id": str(current_user["_id"])}
    elif current_user["user_type"] == "operator":
        # Get operator profile first
        operator_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
        if not operator_profile:
            return {"bookings": [], "count": 0}
        query = {"operator_id": str(operator_profile["_id"])}
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    
    bookings = []
    cursor = db.bookings.find(query).sort("created_at", -1)
    
    async for booking in cursor:
        booking["_id"] = str(booking["_id"])
        bookings.append(booking)
    
    return {"bookings": bookings, "count": len(bookings)}


@router.get("/{booking_id}")
async def get_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get booking details"""
    db = await get_database()
    
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify access
    user_id = str(current_user["_id"])
    if booking["tourist_id"] != user_id:
        # Check if current user is the operator
        if current_user["user_type"] == "operator":
            operator_profile = await db.operator_profiles.find_one({"user_id": user_id})
            if not operator_profile or booking["operator_id"] != str(operator_profile["_id"]):
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    booking["_id"] = str(booking["_id"])
    return booking


@router.put("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status_update: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update booking status (operator only)"""
    if current_user["user_type"] != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can update booking status"
        )
    
    db = await get_database()
    
    # Get operator profile
    operator_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    if not operator_profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    # Verify booking belongs to this operator
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["operator_id"] != str(operator_profile["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update status
    from datetime import datetime
    result = await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "booking_status.status": status_update.get("status"),
                "booking_status.updated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Booking status updated successfully"}


@router.post("/ratings", status_code=status.HTTP_201_CREATED)
async def create_rating(
    rating: RatingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a rating for an operator"""
    if current_user["user_type"] != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tourists can create ratings"
        )
    
    db = await get_database()
    
    # Verify booking exists and belongs to user
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(rating.booking_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["tourist_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if booking is completed
    if booking["booking_status"]["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only rate completed bookings"
        )
    
    # Check if rating already exists
    existing_rating = await db.ratings.find_one({"booking_id": rating.booking_id})
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating already exists for this booking"
        )
    
    # Create rating
    rating_dict = rating.model_dump()
    rating_dict["tourist_id"] = str(current_user["_id"])
    
    from datetime import datetime
    rating_dict["created_at"] = datetime.utcnow()
    
    result = await db.ratings.insert_one(rating_dict)
    
    # Update operator's average rating
    ratings = []
    cursor = db.ratings.find({"operator_id": rating.operator_id})
    async for r in cursor:
        ratings.append(r["rating"])
    
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        await db.operator_profiles.update_one(
            {"_id": ObjectId(rating.operator_id)},
            {
                "$set": {
                    "average_rating": round(avg_rating, 2),
                    "total_reviews": len(ratings)
                }
            }
        )
    
    return {
        "message": "Rating created successfully",
        "rating_id": str(result.inserted_id)
    }


@router.get("/ratings/operator/{operator_id}")
async def get_operator_ratings(operator_id: str):
    """Get all ratings for an operator"""
    db = await get_database()
    
    ratings = []
    cursor = db.ratings.find({"operator_id": operator_id}).sort("created_at", -1)
    
    async for rating in cursor:
        rating["_id"] = str(rating["_id"])
        # Get tourist info
        try:
            tourist = await db.users.find_one({"_id": ObjectId(rating["tourist_id"])})
            if tourist:
                rating["tourist_name"] = tourist.get("full_name", "Anonymous")
        except:
            rating["tourist_name"] = "Anonymous"
        
        ratings.append(rating)
    
    return {"ratings": ratings, "count": len(ratings)}

@router.get("/ratings/booking/{booking_id}")
async def get_booking_rating(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Get rating for a specific booking (tourist view)"""
    if current_user["user_type"] != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tourists can view their ratings"
        )
    
    db = await get_database()
    
    try:
        rating = await db.ratings.find_one({"booking_id": booking_id})
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    if not rating:
        return None
    
    # Verify it belongs to the current user
    if rating["tourist_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    rating["_id"] = str(rating["_id"])
    return rating


@router.put("/ratings/{rating_id}")
async def update_rating(
    rating_id: str,
    rating_update: RatingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing rating (tourist only)"""
    if current_user["user_type"] != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tourists can update ratings"
        )
    
    db = await get_database()
    
    try:
        rating = await db.ratings.find_one({"_id": ObjectId(rating_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid rating ID")
    
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    # Verify ownership
    if rating["tourist_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from datetime import datetime
    
    # Update rating
    update_data = {
        "rating": rating_update.rating,
        "review": rating_update.review,
        "categories": rating_update.categories,
        "updated_at": datetime.utcnow()
    }
    
    result = await db.ratings.update_one(
        {"_id": ObjectId(rating_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    # Update operator's average rating
    ratings = []
    cursor = db.ratings.find({"operator_id": rating["operator_id"]})
    async for r in cursor:
        ratings.append(r["rating"])
    
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        await db.operator_profiles.update_one(
            {"_id": ObjectId(rating["operator_id"])},
            {
                "$set": {
                    "average_rating": round(avg_rating, 2),
                    "total_reviews": len(ratings)
                }
            }
        )
    
    return {"message": "Rating updated successfully"}