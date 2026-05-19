from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_database
from ..models.quote import QuoteRequestCreate, QuoteResponseCreate
from ..routers.auth import get_current_user

router = APIRouter(prefix="/quotes", tags=["Quotes"])


def _serialize_quote(doc, operator_profile_id: str | None = None):
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    if operator_profile_id:
        doc["responded_by_me"] = any(
            resp.get("operator_id") == operator_profile_id for resp in doc.get("responses", [])
        )
    if "responses" in doc:
        for resp in doc["responses"]:
            if isinstance(resp.get("created_at"), datetime):
                resp["created_at"] = resp["created_at"]
    return doc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_quote_request(
    quote: QuoteRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can request quotes")

    if not quote.locations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add at least one location to request a quote")

    for loc in quote.locations:
        if not loc.coordinates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each location needs coordinates so operators can view it on the map"
            )

    db = await get_database()
    payload = quote.model_dump()
    payload["tourist_id"] = str(current_user["_id"])
    payload["tourist_name"] = current_user.get("full_name")
    payload["status"] = "open"
    payload["responses"] = []
    payload["created_at"] = datetime.now(timezone.utc)
    payload["updated_at"] = datetime.now(timezone.utc)

    result = await db.quote_requests.insert_one(payload)
    payload["_id"] = str(result.inserted_id)
    return {"message": "Quote request published", "quote": payload}


@router.get("/my")
async def get_my_quote_requests(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can view their quotes")

    db = await get_database()
    quotes = []
    cursor = db.quote_requests.find({"tourist_id": str(current_user["_id"])}).sort("created_at", -1)
    async for q in cursor:
        quotes.append(_serialize_quote(q))
    return {"quotes": quotes, "count": len(quotes)}


@router.get("/inbox")
async def get_operator_quote_inbox(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only operators can view quote inbox")

    db = await get_database()
    operator_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    if not operator_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    operator_profile_id = str(operator_profile["_id"])

    quotes = []
    cursor = db.quote_requests.find({"status": {"$ne": "closed"}}).sort("created_at", -1)
    async for q in cursor:
        quotes.append(_serialize_quote(q, operator_profile_id=operator_profile_id))

    return {"quotes": quotes, "count": len(quotes)}


@router.post("/{quote_id}/respond", status_code=status.HTTP_201_CREATED)
async def respond_to_quote(
    quote_id: str,
    response: QuoteResponseCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only operators can respond")

    db = await get_database()
    operator_profile = await db.operator_profiles.find_one({"user_id": str(current_user["_id"])})
    if not operator_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    try:
        quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid quote ID")

    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    if quote.get("status") == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote is closed")

    response_entry = {
        "operator_id": str(operator_profile["_id"]),
        "operator_user_id": str(current_user["_id"]),
        "operator_name": operator_profile.get("business_name"),
        "amount": response.amount,
        "message": response.message,
        "created_at": datetime.now(timezone.utc)
    }

    await db.quote_requests.update_one(
        {"_id": ObjectId(quote_id)},
        {
            "$push": {"responses": response_entry},
            "$set": {"status": "responded", "updated_at": datetime.now(timezone.utc)}
        }
    )

    quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
    return {"message": "Response submitted", "quote": _serialize_quote(quote, operator_profile_id=str(operator_profile["_id"]))}


@router.post("/{quote_id}/close")
async def close_quote_request(quote_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can close quotes")

    db = await get_database()
    try:
        quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid quote ID")

    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    if quote.get("tourist_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to close this quote")

    await db.quote_requests.update_one(
        {"_id": ObjectId(quote_id)},
        {"$set": {"status": "closed", "updated_at": datetime.now(timezone.utc)}}
    )

    return {"message": "Quote closed"}

@router.get("/search/locations")
async def search_operator_locations(query: str):
    """
    Search for locations offered by operators.
    Returns a list of locations with operator information.
    """
    if not query or len(query.strip()) < 2:
        return {"global": [], "from_operators": []}
    
    db = await get_database()
    
    # Search in operator serving areas
    operator_locations = []
    
    # Use regex for case-insensitive search
    search_regex = {"$regex": query, "$options": "i"}
    
    # Find operators with matching serving areas
    operators = await db.operator_profiles.find({
        "serving_areas": {
            "$elemMatch": {
                "$or": [
                    {"area_name": search_regex},
                    {"state": search_regex},
                    {"country": search_regex},
                    {"sub_locations.name": search_regex},
                    {"sub_locations.description": search_regex}
                ]
            }
        }
    }).to_list(20)
    
    # Extract matching locations from operators
    seen_locations = set()
    normalized_query = query.lower().strip()

    for operator in operators:
        operator_name = operator.get("business_name", "Unknown Operator")
        operator_id = str(operator["_id"])
        
        for area in operator.get("serving_areas", []):
            # Check if this area matches the query
            area_name = area.get("area_name", "")
            state = area.get("state", "")
            country = area.get("country", "")
            sub_locations = area.get("sub_locations", [])

            area_match = (
                normalized_query in area_name.lower()
                or normalized_query in state.lower()
                or normalized_query in country.lower()
            )

            sub_location_match = any(
                normalized_query in sub.get("name", "").lower()
                or normalized_query in (sub.get("description", "") or "").lower()
                for sub in sub_locations
            )
            
            if area_match or sub_location_match:
                
                location_key = f"{area_name}|{state}|{country}"
                if location_key not in seen_locations:
                    seen_locations.add(location_key)
                    
                    coordinates = area.get("coordinates") or {}
                    operator_locations.append({
                        "id": f"operator_{operator_id}_{area_name}",
                        "name": area_name,
                        "state": state,
                        "country": country,
                        "lat": coordinates.get("latitude"),
                        "lng": coordinates.get("longitude"),
                        "type": "operator_location",
                        "operator_name": operator_name,
                        "operator_id": operator_id,
                        "sub_locations": [
                            sub.get("name") for sub in sub_locations if sub.get("name")
                        ]
                    })
    
    return {
        "from_operators": operator_locations
    }

@router.get("/destinations")
async def get_all_quote_destinations():
    """
    Get all unique destinations from quote requests.
    Returns list of destinations and detailed destination info with state/country.
    """
    db = await get_database()
    
    destinations = []
    destinations_set = set()
    destinations_detailed = []
    detailed_set = set()
    
    # Fetch all quote requests
    cursor = db.quote_requests.find({"status": {"$ne": "closed"}})
    async for quote in cursor:
        for location in quote.get("locations", []):
            location_name = location.get("name", "").strip()
            state = location.get("state", "").strip()
            country = location.get("country", "").strip()
            
            # Add unique location name
            if location_name and location_name not in destinations_set:
                destinations_set.add(location_name)
                destinations.append(location_name)
            
            # Add detailed location info
            if location_name:
                detail_key = f"{location_name}|{state}|{country}"
                if detail_key not in detailed_set:
                    detailed_set.add(detail_key)
                    destinations_detailed.append({
                        "name": location_name,
                        "state": state,
                        "country": country
                    })
    
    # Sort for better UX
    destinations.sort()
    destinations_detailed.sort(key=lambda x: x["name"])
    
    return {
        "destinations": destinations,
        "destinations_with_details": destinations_detailed,
        "count": len(destinations)
    }
