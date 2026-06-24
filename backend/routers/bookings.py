from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor

router = APIRouter(prefix="/bookings", tags=["Bookings"])


async def _refresh_operator_rating_summary(db, operator_id: str) -> None:
    summary = await db.ratings.aggregate(
        [
            {"$match": {"operator_id": operator_id}},
            {
                "$group": {
                    "_id": "$operator_id",
                    "average_rating": {"$avg": "$rating"},
                    "total_reviews": {"$sum": 1},
                }
            },
        ]
    ).to_list(length=1)

    payload = {"average_rating": 0, "total_reviews": 0}
    if summary:
        payload = {
            "average_rating": round(summary[0].get("average_rating", 0), 2),
            "total_reviews": summary[0].get("total_reviews", 0),
        }

    try:
        operator_object_id = ObjectId(operator_id)
    except Exception:
        return

    await db.operator_profiles.update_one(
        {"_id": operator_object_id},
        {"$set": payload},
    )


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
async def get_my_bookings(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Get all bookings for current user"""
    db = await get_database()
    
    if current_user["user_type"] == "tourist":
        query = {"tourist_id": str(current_user["_id"])}
    elif current_user["user_type"] == "operator":
        # Get operator profile first
        operator_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
        if not operator_profile:
            return {
                "bookings": [],
                "count": 0,
                "pagination": {
                    "page_size": page_size,
                    "total_items": 0,
                    "next_cursor": None,
                    "has_more": False,
                },
            }
        query = {"operator_id": str(operator_profile["_id"])}
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    
    total_items = await db.bookings.count_documents(query)
    status_counts = {"all": total_items, "pending": 0, "confirmed": 0, "completed": 0, "cancelled": 0}
    status_rows = await db.bookings.aggregate(
        [
            {"$match": query},
            {
                "$group": {
                    "_id": "$booking_status.status",
                    "count": {"$sum": 1},
                }
            },
        ]
    ).to_list(length=None)
    for row in status_rows:
        status_key = row.get("_id") or "unknown"
        status_counts[status_key] = row.get("count", 0)

    effective_query = dict(query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]

    bookings = []
    operator_ids = set()
    rows = await db.bookings.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])

    for booking in rows:
        booking["_id"] = str(booking["_id"])
        if booking.get("operator_id"):
            operator_ids.add(booking["operator_id"])
        bookings.append(booking)

    operator_name_by_id = {}
    valid_operator_object_ids = []
    for operator_id in operator_ids:
        try:
            valid_operator_object_ids.append(ObjectId(operator_id))
        except Exception:
            continue

    if valid_operator_object_ids:
        async for profile in db.operator_profiles.find({"_id": {"$in": valid_operator_object_ids}}):
            operator_name_by_id[str(profile["_id"])] = profile.get("business_name", "Unknown Operator")

    for booking in bookings:
        booking["operator_name"] = operator_name_by_id.get(
            booking.get("operator_id"),
            "Unknown Operator"
        )
    
    return {
        "bookings": bookings,
        "count": len(bookings),
        "status_counts": status_counts,
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


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

    await _refresh_operator_rating_summary(db, rating.operator_id)
    
    return {
        "message": "Rating created successfully",
        "rating_id": str(result.inserted_id)
    }


@router.get("/ratings/operator/{operator_id}")
async def get_operator_ratings(
    operator_id: str,
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
):
    """Get all ratings for an operator"""
    db = await get_database()
    
    base_query = {"operator_id": operator_id}
    total_items = await db.ratings.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]

    ratings = []
    rows = await db.ratings.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["created_at"], object_id=last_row["_id"])

    for rating in rows:
        rating["_id"] = str(rating["_id"])
        # Get tourist info
        try:
            tourist = await db.users.find_one({"_id": ObjectId(rating["tourist_id"])})
            if tourist:
                rating["tourist_name"] = tourist.get("full_name", "Anonymous")
        except:
            rating["tourist_name"] = "Anonymous"
        
        ratings.append(rating)
    
    return {
        "ratings": ratings,
        "count": len(ratings),
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }

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

    await _refresh_operator_rating_summary(db, rating["operator_id"])
    
    return {"message": "Rating updated successfully"}