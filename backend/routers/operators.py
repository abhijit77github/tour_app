from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from ..models.operator import (
    OperatorProfile, 
    OperatorProfileCreate, 
    OperatorProfileUpdate,
    ServingArea,
    SubLocation
)
from ..models.promotion import PromotionClickCreate, PromotionLocationScope
from ..database import get_database
from ..routers.auth import get_current_operator_access_context, get_current_user
from ..utils.authorization import ensure_membership, ensure_operator_organization
from ..utils.billing import (
    append_configurable_billing_event,
    build_click_idempotency_key,
    build_request_fingerprint,
)

router = APIRouter(prefix="/operators", tags=["Operators"])
MAX_PROMOTED_SEARCH_RESULTS = 3


def _coerce_utc_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_location_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.casefold() if cleaned else None


def _serialize_operator(operator: dict, *, promoted: bool = False, promotion: Optional[dict] = None) -> dict:
    operator["_id"] = str(operator["_id"])
    operator["is_promoted"] = promoted
    operator["promotion_context"] = None
    if promotion:
        operator["promotion_context"] = {
            "promotion_id": str(promotion["_id"]),
            "label": promotion.get("promotion_label", "Promoted"),
            "matched_on": "location",
            "service_type": promotion.get("service_type"),
        }
    return operator


def _promotion_is_eligible(promotion: dict, now: datetime) -> bool:
    if promotion.get("status") != "active":
        return False
    start_at = _coerce_utc_datetime(promotion.get("start_at"))
    end_at = _coerce_utc_datetime(promotion.get("end_at"))
    last_daily_reset_at = _coerce_utc_datetime(promotion.get("last_daily_reset_at"))

    if start_at and start_at > now:
        return False
    if end_at and end_at < now:
        return False

    daily_budget = promotion.get("daily_budget")
    total_budget = promotion.get("total_budget")
    daily_spend = float(promotion.get("daily_spend") or 0)
    total_spend = float(promotion.get("total_spend") or 0)

    if last_daily_reset_at and last_daily_reset_at.date() != now.date():
        daily_spend = 0.0

    if daily_budget is not None and daily_spend >= float(daily_budget):
        return False
    if total_budget is not None and total_spend >= float(total_budget):
        return False

    return True


async def _get_matching_promotions(
    db,
    *,
    area_name: Optional[str],
    state: Optional[str],
    country: Optional[str],
    service_type: Optional[str],
) -> List[dict]:
    if not any([area_name, state, country]):
        return []

    scope = PromotionLocationScope(area_name=area_name, state=state, country=country)
    query: Dict[str, object] = {
        "status": "active",
        "start_at": {"$lte": datetime.now(timezone.utc)},
        "end_at": {"$gte": datetime.now(timezone.utc)},
    }

    normalized_area = _normalize_location_value(scope.area_name)
    normalized_state = _normalize_location_value(scope.state)
    normalized_country = _normalize_location_value(scope.country)

    if normalized_area:
        query["normalized_location_scope.area_name"] = normalized_area
    if normalized_state:
        query["normalized_location_scope.state"] = normalized_state
    if normalized_country:
        query["normalized_location_scope.country"] = normalized_country
    if service_type:
        query["service_type"] = service_type

    promotions = await db.location_promotions.find(query).sort([
        ("priority", -1),
        ("bid_amount", -1),
        ("updated_at", -1),
    ]).to_list(length=20)

    now = datetime.now(timezone.utc)
    eligible_promotions = [promotion for promotion in promotions if _promotion_is_eligible(promotion, now)]
    if not eligible_promotions:
        return []

    operator_profile_ids = list({promotion.get("operator_profile_id") for promotion in eligible_promotions if promotion.get("operator_profile_id")})
    active_plans = await db.provider_plans.find(
        {
            "operator_profile_id": {"$in": operator_profile_ids},
            "plan_status": "active",
            "credits_remaining": {"$gt": 0},
        }
    ).to_list(length=len(operator_profile_ids) or 1)
    active_plan_operator_ids = {plan.get("operator_profile_id") for plan in active_plans}
    return [promotion for promotion in eligible_promotions if promotion.get("operator_profile_id") in active_plan_operator_ids]


async def _increment_promotion_impressions(db, promotions: List[dict]) -> None:
    if not promotions:
        return

    for promotion in promotions:
        now = datetime.now(timezone.utc)
        set_data = {"last_served_at": now, "updated_at": now}
        if promotion.get("last_daily_reset_at") is None or promotion["last_daily_reset_at"].date() != now.date():
            set_data["last_daily_reset_at"] = now
            set_data["daily_spend"] = 0
        await db.location_promotions.update_one(
            {"_id": promotion["_id"]},
            {
                "$inc": {"total_impressions": 1},
                "$set": set_data,
            },
        )


@router.post("/promotions/{promotion_id}/click")
async def track_promotion_click(
    promotion_id: str,
    payload: PromotionClickCreate,
    request: Request,
):
    """Track a click on a promoted operator result and accrue CPC spend."""
    db = await get_database()

    try:
        promotion = await db.location_promotions.find_one({"_id": ObjectId(promotion_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid promotion ID") from exc

    if not promotion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    now = datetime.now(timezone.utc)
    if not _promotion_is_eligible(promotion, now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion is not eligible for click tracking")

    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    idempotency_key = build_click_idempotency_key(
        promotion_id=str(promotion["_id"]),
        source=payload.source,
        session_id=payload.session_id,
        request_id=payload.request_id,
        client_host=client_host,
        user_agent=user_agent,
        current_time=now,
    )
    existing_event = await db.billing_event_log.find_one({"idempotency_key": idempotency_key})
    if existing_event:
        return {
            "message": "Promotion click already processed",
            "billable": existing_event.get("is_billable", False),
            "reason": "duplicate_click",
        }

    bid_amount = float(promotion.get("bid_amount") or 0)
    set_data = {"updated_at": now, "last_served_at": now}
    if promotion.get("last_daily_reset_at") is None or promotion["last_daily_reset_at"].date() != now.date():
        set_data["last_daily_reset_at"] = now
        set_data["daily_spend"] = 0

    request_fingerprint = build_request_fingerprint(
        session_id=payload.session_id,
        request_id=payload.request_id,
        client_host=client_host,
        user_agent=user_agent,
    )

    billing_result = await append_configurable_billing_event(
        db,
        operator_profile_id=promotion.get("operator_profile_id"),
        promotion_id=str(promotion["_id"]),
        source_surface="search",
        event_type="profile_click",
        source_reference_type="promotion_click",
        source_reference_id=str(promotion["_id"]),
        anonymous_session_id=payload.session_id,
        request_fingerprint=request_fingerprint,
        outcome_reason="charged",
        metadata={
            "source": payload.source,
            "area_name": payload.area_name,
            "state": payload.state,
            "country": payload.country,
            "service_type": payload.service_type,
            "request_id": payload.request_id,
            "client_host": client_host,
            "user_agent": (user_agent or "")[:120],
        },
        currency_amount_on_success=bid_amount,
        notes=f"Unique promoted search click for promotion {promotion_id}",
        idempotency_key=idempotency_key,
    )

    if not billing_result.get("inserted"):
        return {
            "message": "Promotion click already processed",
            "billable": False,
            "reason": "duplicate_click",
        }

    is_billable = billing_result.get("charged", False)
    outcome_reason = billing_result.get("charge_error") or "charged"

    if is_billable:
        await db.location_promotions.update_one(
            {"_id": promotion["_id"]},
            {
                "$inc": {
                    "total_clicks": 1,
                    "total_spend": bid_amount,
                    "daily_spend": bid_amount,
                },
                "$set": set_data,
            },
        )

    if is_billable:
        await db.promotion_events.insert_one(
            {
                "promotion_id": str(promotion["_id"]),
                "operator_profile_id": promotion.get("operator_profile_id"),
                "source": payload.source,
                "area_name": payload.area_name,
                "state": payload.state,
                "country": payload.country,
                "service_type": payload.service_type,
                "bid_amount": bid_amount,
                "credits_charged": billing_result.get("configured_credits", 0),
                "created_at": now,
            }
        )

    return {
        "message": "Promotion click processed",
        "billable": is_billable,
        "reason": outcome_reason,
    }


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
    profile_dict["service_types"] = profile_dict.get("service_types") or ["tour"]
    profile_dict["car_services"] = profile_dict.get("car_services") or []
    profile_dict["average_rating"] = 0.0
    profile_dict["total_reviews"] = 0
    now = datetime.now(timezone.utc)
    profile_dict["created_at"] = now
    profile_dict["updated_at"] = now
    
    result = await db.operator_profiles.insert_one(profile_dict)
    stored_profile = {**profile_dict, "_id": result.inserted_id}
    organization = await ensure_operator_organization(db, profile=stored_profile)
    await ensure_membership(
        db,
        organization_id=str(organization["_id"]),
        principal_type="user",
        principal_id=str(current_user["_id"]),
        role_keys=["operator_owner"],
    )
    
    return {
        "message": "Operator profile created successfully",
        "profile_id": str(result.inserted_id)
    }


@router.get("/profile/me")
async def get_my_profile(access_context: dict = Depends(get_current_operator_access_context)):
    """Get current operator's profile"""
    db = await get_database()
    profile = await db.operator_profiles.find_one({"_id": ObjectId(access_context["operator_profile"]["_id"])})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    profile["_id"] = str(profile["_id"])
    return profile


@router.put("/profile/me")
async def update_my_profile(
    profile_update: OperatorProfileUpdate,
    access_context: dict = Depends(get_current_operator_access_context)
):
    """Update current operator's profile"""
    db = await get_database()
    profile_id = access_context["operator_profile"]["_id"]
    
    # Get update data (exclude None values)
    update_data = {k: v for k, v in profile_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Try to update existing profile
    result = await db.operator_profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": update_data}
    )
    
    # If no profile exists, create one
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")
    
    return {"message": "Profile updated successfully"}


@router.post("/profile/serving-areas")
async def add_serving_area(
    serving_area: ServingArea,
    access_context: dict = Depends(get_current_operator_access_context)
):
    """Add a new serving area"""
    for sub in serving_area.sub_locations:
        if not sub.coordinates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each sub-location must include coordinates"
            )

    db = await get_database()
    
    result = await db.operator_profiles.update_one(
        {"_id": ObjectId(access_context["operator_profile"]["_id"])},
        {
            "$push": {"serving_areas": serving_area.model_dump()},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area added successfully"}


@router.put("/profile/serving-areas/{area_index}")
async def update_serving_area(
    area_index: int,
    serving_area: ServingArea,
    access_context: dict = Depends(get_current_operator_access_context)
):
    """Update an existing serving area by index"""
    # Validate coordinates for all sub-locations
    for sub in serving_area.sub_locations:
        if not sub.coordinates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each sub-location must include coordinates"
            )

    db = await get_database()
    profile_id = access_context["operator_profile"]["_id"]
    
    # Get current profile to verify area exists
    profile = await db.operator_profiles.find_one({"_id": ObjectId(profile_id)})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    if area_index < 0 or area_index >= len(profile.get("serving_areas", [])):
        raise HTTPException(status_code=404, detail="Serving area not found")
    
    # Update the specific serving area at the given index
    result = await db.operator_profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                f"serving_areas.{area_index}": serving_area.model_dump(),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area updated successfully"}


@router.delete("/profile/serving-areas/{area_index}")
async def delete_serving_area(
    area_index: int,
    access_context: dict = Depends(get_current_operator_access_context)
):
    """Delete a serving area by index"""
    db = await get_database()
    profile_id = access_context["operator_profile"]["_id"]
    
    # Get current profile to verify area exists
    profile = await db.operator_profiles.find_one({"_id": ObjectId(profile_id)})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    if area_index < 0 or area_index >= len(profile.get("serving_areas", [])):
        raise HTTPException(status_code=404, detail="Serving area not found")
    
    from datetime import datetime
    
    # Remove the serving area at the given index
    serving_areas = profile.get("serving_areas", [])
    serving_areas.pop(area_index)
    
    result = await db.operator_profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "serving_areas": serving_areas,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Operator profile not found")
    
    return {"message": "Serving area deleted successfully"}


@router.get("/serving-areas")
async def get_all_serving_areas():
    """Get all unique serving areas from all operators"""
    db = await get_database()
    
    areas = []
    states = set()
    countries = set()
    detailed_areas = []
    detailed_set = set()
    
    # Fetch all operator profiles and their serving areas
    cursor = db.operator_profiles.find({})
    async for operator in cursor:
        for area in operator.get("serving_areas", []):
            area_name = area.get("area_name", "").strip()
            state = area.get("state", "").strip()
            country = area.get("country", "").strip()
            
            # Add unique area name
            if area_name and area_name not in areas:
                areas.append(area_name)
            
            # Track states and countries
            if state:
                states.add(state)
            if country:
                countries.add(country)
            
            # Add detailed area info
            if area_name:
                detail_key = f"{area_name}|{state}|{country}"
                if detail_key not in detailed_set:
                    detailed_set.add(detail_key)
                    detailed_areas.append({
                        "name": area_name,
                        "state": state,
                        "country": country
                    })
    
    # Sort for better UX
    areas.sort()
    detailed_areas.sort(key=lambda x: x["name"])
    states_list = sorted(list(states))
    countries_list = sorted(list(countries))
    
    return {
        "areas": areas,
        "areas_with_details": detailed_areas,
        "states": states_list,
        "countries": countries_list,
        "count": len(areas)
    }


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

    ratings = []
    async for rating in db.ratings.find({"operator_id": operator_id}):
        ratings.append(float(rating.get("rating", 0) or 0))

    if ratings:
        profile["average_rating"] = round(sum(ratings) / len(ratings), 2)
        profile["total_reviews"] = len(ratings)
    else:
        profile["average_rating"] = 0.0
        profile["total_reviews"] = 0
    
    profile["_id"] = str(profile["_id"])
    return profile


@router.get("/search/location")
async def search_operators_by_location(
    operator_name: Optional[str] = None,
    area_name: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    service_type: Optional[str] = None,
):
    """Search operators by operator name, location, and optional service type (tour, car)"""
    db = await get_database()
    
    # Build search query
    query = {}
    if operator_name:
        query["business_name"] = {"$regex": operator_name, "$options": "i"}
    if area_name:
        query["serving_areas.area_name"] = {"$regex": area_name, "$options": "i"}
    if state:
        query["serving_areas.state"] = {"$regex": state, "$options": "i"}
    if country:
        query["serving_areas.country"] = {"$regex": country, "$options": "i"}
    if service_type:
        query["service_types"] = service_type
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one search parameter is required"
        )
    
    organic_operators = []
    organic_cursor = db.operator_profiles.find(query).sort("average_rating", -1)

    async for operator in organic_cursor:
        organic_operators.append(operator)

    promotions = await _get_matching_promotions(
        db,
        area_name=area_name,
        state=state,
        country=country,
        service_type=service_type,
    )

    promoted_results = []
    served_promotions = []
    seen_operator_ids = set()

    for promotion in promotions:
        operator_id = promotion.get("operator_profile_id")
        if not operator_id or operator_id in seen_operator_ids:
            continue

        try:
            promoted_operator = await db.operator_profiles.find_one({"_id": ObjectId(operator_id)})
        except Exception:
            continue

        if not promoted_operator:
            continue

        promoted_results.append(_serialize_operator(promoted_operator, promoted=True, promotion=promotion))
        served_promotions.append(promotion)
        seen_operator_ids.add(operator_id)

        if len(promoted_results) >= MAX_PROMOTED_SEARCH_RESULTS:
            break

    organic_results = []
    for operator in organic_operators:
        operator_id = str(operator["_id"])
        if operator_id in seen_operator_ids:
            continue
        organic_results.append(_serialize_operator(operator, promoted=False))
        seen_operator_ids.add(operator_id)

    await _increment_promotion_impressions(db, served_promotions)

    operators = promoted_results + organic_results
    return {
        "operators": operators,
        "count": len(operators),
        "promoted_count": len(promoted_results),
        "organic_count": len(organic_results),
    }
