import base64
from datetime import datetime, timedelta, timezone
import json
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_database
from ..models.quote import QuoteRequestCreate, QuoteResponseCreate
from ..routers.auth import get_current_operator_access_context, get_current_user
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor

router = APIRouter(prefix="/quotes", tags=["Quotes"])

SUPPORTED_QUOTE_SORTS = ("newest", "unresponded_first", "highest_budget", "travel_soonest")
QUOTE_BUDGET_BANDS = ("budget", "mid", "premium")
QUOTE_TRAVEL_WINDOW_FILTERS = ("all", "next_30_days", "days_31_90", "days_90_plus", "unspecified")
UNSPECIFIED_TRAVEL_DATE = datetime(9999, 12, 31, tzinfo=timezone.utc)


def _normalize_quote_filter_now(now: datetime | None = None) -> datetime:
    base_now = now or datetime.now(timezone.utc)
    if base_now.tzinfo is None:
        base_now = base_now.replace(tzinfo=timezone.utc)
    return base_now.replace(hour=0, minute=0, second=0, microsecond=0)


def _build_quote_budget_band_expression(field_name: str = "$budget") -> dict:
    return {
        "$switch": {
            "branches": [
                {
                    "case": {
                        "$and": [
                            {"$ne": [{"$ifNull": [field_name, None]}, None]},
                            {"$lt": [field_name, 20000]},
                        ]
                    },
                    "then": "budget",
                },
                {
                    "case": {
                        "$and": [
                            {"$ne": [{"$ifNull": [field_name, None]}, None]},
                            {"$lt": [field_name, 50000]},
                        ]
                    },
                    "then": "mid",
                },
                {
                    "case": {"$ne": [{"$ifNull": [field_name, None]}, None]},
                    "then": "premium",
                },
            ],
            "default": None,
        }
    }


def _build_quote_budget_match(budget_band: str) -> dict:
    if budget_band == "budget":
        return {"budget": {"$lt": 20000}}
    if budget_band == "mid":
        return {"budget": {"$gte": 20000, "$lt": 50000}}
    if budget_band == "premium":
        return {"budget": {"$gte": 50000}}
    return {}


def _build_quote_travel_window_bucket_expression(*, now: datetime) -> dict:
    next_30_days = now + timedelta(days=30)
    next_90_days = now + timedelta(days=90)
    return {
        "$switch": {
            "branches": [
                {"case": {"$eq": ["$sort_travel_start", UNSPECIFIED_TRAVEL_DATE]}, "then": "unspecified"},
                {
                    "case": {
                        "$and": [
                            {"$gte": ["$sort_travel_start", now]},
                            {"$lte": ["$sort_travel_start", next_30_days]},
                        ]
                    },
                    "then": "next_30_days",
                },
                {
                    "case": {
                        "$and": [
                            {"$gt": ["$sort_travel_start", next_30_days]},
                            {"$lte": ["$sort_travel_start", next_90_days]},
                        ]
                    },
                    "then": "days_31_90",
                },
                {"case": {"$gt": ["$sort_travel_start", next_90_days]}, "then": "days_90_plus"},
            ],
            "default": "unspecified",
        }
    }


def _build_quote_travel_normalization_stage() -> dict:
    return {
        "$addFields": {
            "sort_travel_start": {
                "$ifNull": [
                    "$travel_start_date",
                    {
                        "$dateFromString": {
                            "dateString": {
                                "$trim": {
                                    "input": {
                                        "$arrayElemAt": [
                                            {"$split": [{"$ifNull": ["$travel_window", ""]}, " to "]},
                                            0,
                                        ]
                                    }
                                }
                            },
                            "timezone": "UTC",
                            "onError": UNSPECIFIED_TRAVEL_DATE,
                            "onNull": UNSPECIFIED_TRAVEL_DATE,
                        }
                    },
                ]
            }
        }
    }


def _requires_quote_travel_stage(*, sort_mode: str, travel_window: str) -> bool:
    return sort_mode == "travel_soonest" or travel_window != "all"


def _build_quote_travel_window_match(*, travel_window: str, now: datetime) -> dict:
    next_30_days = now + timedelta(days=30)
    next_90_days = now + timedelta(days=90)

    if travel_window == "next_30_days":
        return {"sort_travel_start": {"$gte": now, "$lte": next_30_days}}
    if travel_window == "days_31_90":
        return {"sort_travel_start": {"$gt": next_30_days, "$lte": next_90_days}}
    if travel_window == "days_90_plus":
        return {"sort_travel_start": {"$gt": next_90_days, "$lt": UNSPECIFIED_TRAVEL_DATE}}
    if travel_window == "unspecified":
        return {"sort_travel_start": UNSPECIFIED_TRAVEL_DATE}
    return {}


def _build_quote_filter_option_labels() -> dict:
    return {
        "budget": {
            "budget": "Budget under 20k",
            "mid": "Mid 20k-50k",
            "premium": "Premium 50k+",
        },
        "travel_window": {
            "next_30_days": "Next 30 days",
            "days_31_90": "1 to 3 months",
            "days_90_plus": "Later than 3 months",
            "unspecified": "Flexible or unspecified",
        },
    }


def _parse_quote_travel_start_date(travel_window) -> datetime | None:
    if not travel_window:
        return None

    if isinstance(travel_window, dict):
        start_candidate = travel_window.get("start_date") or travel_window.get("from")
    else:
        start_candidate = str(travel_window).split(" to ", 1)[0].strip()

    if not start_candidate:
        return None

    normalized = start_candidate.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(start_candidate, "%Y-%m-%d")
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _build_operator_quote_inbox_query(
    *,
    operator_profile_id: str,
    status_filter: str,
    search: str | None,
    location_filter: str | None,
    budget_band: str,
) -> dict:
    query: dict = {"status": {"$ne": "closed"}}

    if status_filter == "responded":
        query["responses.operator_id"] = operator_profile_id
    elif status_filter == "new":
        query["responses"] = {"$not": {"$elemMatch": {"operator_id": operator_profile_id}}}

    normalized_search = (search or "").strip()
    if normalized_search:
        escaped_query = re.escape(normalized_search[:80])
        query["$or"] = [
            {"tourist_name": {"$regex": escaped_query, "$options": "i"}},
            {"notes": {"$regex": escaped_query, "$options": "i"}},
            {"preferences": {"$regex": escaped_query, "$options": "i"}},
            {"locations.name": {"$regex": escaped_query, "$options": "i"}},
            {"locations.state": {"$regex": escaped_query, "$options": "i"}},
            {"locations.country": {"$regex": escaped_query, "$options": "i"}},
        ]

    normalized_location = (location_filter or "").strip()
    if normalized_location:
        query["locations"] = {
            "$elemMatch": {
                "name": {
                    "$regex": f"^{re.escape(normalized_location[:80])}$",
                    "$options": "i",
                }
            }
        }

    query.update(_build_quote_budget_match(budget_band))

    return query


def _build_operator_quote_sort_spec(sort_mode: str) -> list[tuple[str, int]]:
    if sort_mode == "unresponded_first":
        return [("sort_responded_rank", 1), ("created_at", -1), ("_id", -1)]
    if sort_mode == "highest_budget":
        return [("sort_budget", -1), ("created_at", -1), ("_id", -1)]
    if sort_mode == "travel_soonest":
        return [("sort_travel_start", 1), ("created_at", -1), ("_id", -1)]
    return [("created_at", -1), ("_id", -1)]


def _encode_quote_inbox_cursor(*, sort_mode: str, row: dict) -> str:
    payload = {
        "sort_mode": sort_mode,
        "created_at": row["created_at"].isoformat(),
        "object_id": str(row["_id"]),
    }
    if sort_mode == "unresponded_first":
        payload["responded_rank"] = row.get("sort_responded_rank", 1)
    elif sort_mode == "highest_budget":
        payload["budget"] = row.get("sort_budget", 0)
    elif sort_mode == "travel_soonest":
        payload["travel_start"] = row.get("sort_travel_start").isoformat() if row.get("sort_travel_start") else None
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _decode_quote_inbox_cursor(cursor: str) -> dict:
    decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    payload = json.loads(decoded)
    payload["created_at"] = datetime.fromisoformat(payload["created_at"])
    payload["object_id"] = ObjectId(payload["object_id"])
    if payload["created_at"].tzinfo is None:
        payload["created_at"] = payload["created_at"].replace(tzinfo=timezone.utc)
    if payload.get("travel_start"):
        payload["travel_start"] = datetime.fromisoformat(payload["travel_start"])
        if payload["travel_start"].tzinfo is None:
            payload["travel_start"] = payload["travel_start"].replace(tzinfo=timezone.utc)
    return payload


def _build_quote_inbox_cursor_match(*, sort_mode: str, cursor_payload: dict) -> dict:
    created_at = cursor_payload["created_at"]
    object_id = cursor_payload["object_id"]

    if sort_mode == "unresponded_first":
        responded_rank = cursor_payload.get("responded_rank", 1)
        return {
            "$or": [
                {"sort_responded_rank": {"$gt": responded_rank}},
                {"sort_responded_rank": responded_rank, "created_at": {"$lt": created_at}},
                {"sort_responded_rank": responded_rank, "created_at": created_at, "_id": {"$lt": object_id}},
            ]
        }

    if sort_mode == "highest_budget":
        budget = cursor_payload.get("budget", 0)
        return {
            "$or": [
                {"sort_budget": {"$lt": budget}},
                {"sort_budget": budget, "created_at": {"$lt": created_at}},
                {"sort_budget": budget, "created_at": created_at, "_id": {"$lt": object_id}},
            ]
        }

    if sort_mode == "travel_soonest":
        travel_start = cursor_payload.get("travel_start")
        if travel_start is None:
            return {
                "$or": [
                    {"sort_travel_start": None, "created_at": {"$lt": created_at}},
                    {"sort_travel_start": None, "created_at": created_at, "_id": {"$lt": object_id}},
                ]
            }
        return {
            "$or": [
                {"sort_travel_start": {"$gt": travel_start}},
                {"sort_travel_start": travel_start, "created_at": {"$lt": created_at}},
                {"sort_travel_start": travel_start, "created_at": created_at, "_id": {"$lt": object_id}},
            ]
        }

    return build_desc_created_cursor_match(created_at=created_at, object_id=object_id)


def _build_quote_inbox_pipeline(
    *,
    query: dict,
    operator_profile_id: str,
    sort_mode: str,
    page_size: int,
    cursor: str | None,
    travel_window: str,
) -> list[dict]:
    pipeline: list[dict] = [{"$match": query}]
    normalized_now = _normalize_quote_filter_now()

    if _requires_quote_travel_stage(sort_mode=sort_mode, travel_window=travel_window):
        pipeline.append(_build_quote_travel_normalization_stage())
        travel_window_match = _build_quote_travel_window_match(travel_window=travel_window, now=normalized_now)
        if travel_window_match:
            pipeline.append({"$match": travel_window_match})

    if sort_mode == "unresponded_first":
        pipeline.append(
            {
                "$addFields": {
                    "sort_responded_rank": {
                        "$cond": [
                            {
                                "$gt": [
                                    {
                                        "$size": {
                                            "$filter": {
                                                "input": {"$ifNull": ["$responses", []]},
                                                "as": "response",
                                                "cond": {"$eq": ["$$response.operator_id", operator_profile_id]},
                                            }
                                        }
                                    },
                                    0,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                }
            }
        )
    elif sort_mode == "highest_budget":
        pipeline.append({"$addFields": {"sort_budget": {"$ifNull": ["$budget", 0]}}})

    if cursor:
        cursor_payload = _decode_quote_inbox_cursor(cursor)
        if cursor_payload.get("sort_mode") != sort_mode:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cursor sort mode mismatch")
        pipeline.append({"$match": _build_quote_inbox_cursor_match(sort_mode=sort_mode, cursor_payload=cursor_payload)})

    pipeline.extend([
        {"$sort": dict(_build_operator_quote_sort_spec(sort_mode))},
        {"$limit": page_size + 1},
    ])
    return pipeline


def _build_itinerary_snapshot(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title"),
        "summary": doc.get("summary"),
        "primary_location": doc.get("primary_location"),
        "route_locations": doc.get("route_locations", []),
        "duration_days": doc.get("duration_days"),
        "trip_styles": doc.get("trip_styles", []),
        "travelers": doc.get("travelers"),
        "budget_band": doc.get("budget_band"),
        "notes": doc.get("notes"),
        "days": doc.get("days", []),
        "source_type": doc.get("source_type"),
        "source_template_ids": doc.get("source_template_ids", []),
    }


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


async def get_user_quote_limit(user_id: str, db) -> dict:
    """
    Get user's membership tier and corresponding quote limit.
    
    Returns:
        dict with keys: tier, limit, tier_name
    """
    from bson import ObjectId
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        # Default to free tier if user not found
        return {"tier": "free", "limit": 5, "tier_name": "Free"}
    
    tier = user.get("membership_tier", "free")
    
    # Check if membership is expired
    expires_at = user.get("membership_expires_at")
    if expires_at and isinstance(expires_at, datetime):
        if expires_at < datetime.now(timezone.utc):
            tier = "free"  # Downgrade to free if expired
    
    # Get limits from system config
    config = await db.system_config.find_one({"config_key": "quote_limits"})
    if config and "quote_limits" in config:
        limits = config["quote_limits"]
    else:
        # Default limits if config not found
        limits = {"free": 5, "premium": 20, "enterprise": 100}
    
    limit = limits.get(tier, 5)
    tier_name = tier.capitalize()
    
    return {
        "tier": tier,
        "limit": limit,
        "tier_name": tier_name
    }


def get_upgrade_suggestion(current_tier: str) -> str:
    """Get suggested upgrade tier for error messages."""
    if current_tier == "free":
        return "Premium"
    elif current_tier == "premium":
        return "Enterprise"
    return "a higher tier"


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
    
    # Check quote limit before proceeding
    user_limit_info = await get_user_quote_limit(str(current_user["_id"]), db)
    open_count = await db.quote_requests.count_documents({
        "tourist_id": str(current_user["_id"]),
        "status": "open"
    })
    
    if open_count >= user_limit_info["limit"]:
        upgrade_suggestion = get_upgrade_suggestion(user_limit_info["tier"])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your limit of {user_limit_info['limit']} open quote requests. "
                   f"Please close or cancel existing quotes, or upgrade to {upgrade_suggestion} for more quotes."
        )
    
    payload = quote.model_dump()

    itinerary_id = payload.get("attached_itinerary_id")
    if itinerary_id:
        try:
            itinerary = await db.tourist_itineraries.find_one({
                "_id": ObjectId(itinerary_id),
                "tourist_id": str(current_user["_id"]),
                "shareable_to_quote": True,
            })
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attached itinerary ID") from exc

        if not itinerary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attached itinerary not found or not shareable",
            )

        payload["attached_itinerary_snapshot"] = _build_itinerary_snapshot(itinerary)

    payload["tourist_id"] = str(current_user["_id"])
    payload["tourist_name"] = current_user.get("full_name")
    payload["status"] = "open"
    payload["responses"] = []
    payload["travel_start_date"] = _parse_quote_travel_start_date(payload.get("travel_window"))
    payload["created_at"] = datetime.now(timezone.utc)
    payload["updated_at"] = datetime.now(timezone.utc)

    result = await db.quote_requests.insert_one(payload)
    payload["_id"] = str(result.inserted_id)
    return {"message": "Quote request published", "quote": payload}


@router.get("/my")
async def get_my_quote_requests(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=50, description="Number of quotes per page")
):
    """
    Get current user's quote requests with pagination.
    
    Returns paginated quotes with metadata about current page, total count, etc.
    """
    if current_user["user_type"] != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can view their quotes")

    db = await get_database()
    
    # Calculate skip for pagination
    skip = (page - 1) * page_size
    
    # Get total count
    total = await db.quote_requests.count_documents({
        "tourist_id": str(current_user["_id"])
    })
    
    # Get total open quotes count (for quota display)
    open_count = await db.quote_requests.count_documents({
        "tourist_id": str(current_user["_id"]),
        "status": "open"
    })
    
    # Get user's quota information
    user_limit_info = await get_user_quote_limit(str(current_user["_id"]), db)
    
    # Get paginated results
    cursor = db.quote_requests.find({
        "tourist_id": str(current_user["_id"])
    }).sort("created_at", -1).skip(skip).limit(page_size)
    
    quotes = []
    async for q in cursor:
        quotes.append(_serialize_quote(q))
    
    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    has_more = skip + len(quotes) < total
    
    return {
        "quotes": quotes,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_more": has_more
        },
        "quota": {
            "open_count": open_count,
            "limit": user_limit_info["limit"],
            "tier": user_limit_info["tier"],
            "tier_name": user_limit_info["tier_name"],
            "remaining": max(0, user_limit_info["limit"] - open_count)
        }
    }


@router.get("/inbox")
async def get_operator_quote_inbox(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    status_filter: str = Query(default="all", pattern="^(all|new|responded)$"),
    search: str | None = Query(default=None, max_length=80),
    location: str | None = Query(default=None, max_length=80),
    budget_band: str = Query(default="all", pattern="^(all|budget|mid|premium)$"),
    travel_window: str = Query(default="all", pattern="^(all|next_30_days|days_31_90|days_90_plus|unspecified)$"),
    sort_mode: str = Query(default="newest", pattern="^(newest|unresponded_first|highest_budget|travel_soonest)$"),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    operator_profile = access_context["operator_profile"]
    operator_profile_id = str(operator_profile["_id"])

    summary_query = {"status": {"$ne": "closed"}}
    total_items = await db.quote_requests.count_documents(summary_query)
    responded_items = await db.quote_requests.count_documents(
        {
            **summary_query,
            "responses.operator_id": operator_profile_id,
        }
    )
    new_items = max(total_items - responded_items, 0)
    filtered_query = _build_operator_quote_inbox_query(
        operator_profile_id=operator_profile_id,
        status_filter=status_filter,
        search=search,
        location_filter=location,
        budget_band=budget_band,
    )
    if _requires_quote_travel_stage(sort_mode=sort_mode, travel_window=travel_window):
        count_pipeline = [
            {"$match": filtered_query},
            _build_quote_travel_normalization_stage(),
        ]
        travel_window_match = _build_quote_travel_window_match(
            travel_window=travel_window,
            now=_normalize_quote_filter_now(),
        )
        if travel_window_match:
            count_pipeline.append({"$match": travel_window_match})
        count_pipeline.append({"$count": "count"})
        count_rows = await db.quote_requests.aggregate(count_pipeline).to_list(length=1)
        filtered_total_items = count_rows[0]["count"] if count_rows else 0
    else:
        filtered_total_items = await db.quote_requests.count_documents(filtered_query)

    quotes = []
    try:
        pipeline = _build_quote_inbox_pipeline(
            query=filtered_query,
            operator_profile_id=operator_profile_id,
            sort_mode=sort_mode,
            page_size=page_size,
            cursor=cursor,
            travel_window=travel_window,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
    rows = await db.quote_requests.aggregate(pipeline).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = _encode_quote_inbox_cursor(sort_mode=sort_mode, row=last_row)

    for q in rows:
        q.pop("sort_responded_rank", None)
        q.pop("sort_budget", None)
        q.pop("sort_travel_start", None)
        quotes.append(_serialize_quote(q, operator_profile_id=operator_profile_id))

    return {
        "quotes": quotes,
        "count": len(quotes),
        "summary": {
            "total_items": total_items,
            "new_items": new_items,
            "responded_items": responded_items,
        },
        "pagination": {
            "page_size": page_size,
            "total_items": filtered_total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "sort_mode": sort_mode,
        },
    }


@router.get("/inbox/filter-options")
async def get_operator_quote_inbox_filter_options(
    status_filter: str = Query(default="all", pattern="^(all|new|responded)$"),
    search: str | None = Query(default=None, max_length=80),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    operator_profile_id = str(access_context["operator_profile"]["_id"])
    base_query = _build_operator_quote_inbox_query(
        operator_profile_id=operator_profile_id,
        status_filter=status_filter,
        search=search,
        location_filter=None,
        budget_band="all",
    )
    normalized_now = _normalize_quote_filter_now()
    label_maps = _build_quote_filter_option_labels()

    pipeline = [
        {"$match": base_query},
        _build_quote_travel_normalization_stage(),
        {
            "$addFields": {
                "filter_budget_band": _build_quote_budget_band_expression(),
                "filter_travel_window": _build_quote_travel_window_bucket_expression(now=normalized_now),
            }
        },
        {
            "$facet": {
                "locations": [
                    {"$unwind": "$locations"},
                    {"$match": {"locations.name": {"$type": "string", "$ne": ""}}},
                    {"$group": {"_id": "$locations.name", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1, "_id": 1}},
                    {"$limit": 20},
                ],
                "budget_bands": [
                    {"$group": {"_id": "$filter_budget_band", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "travel_windows": [
                    {"$group": {"_id": "$filter_travel_window", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
            }
        },
    ]
    rows = await db.quote_requests.aggregate(pipeline).to_list(length=1)
    facets = rows[0] if rows else {}

    return {
        "filters": {
            "locations": [
                {
                    "value": row["_id"],
                    "label": row["_id"],
                    "count": row["count"],
                }
                for row in facets.get("locations", [])
                if row.get("_id")
            ],
            "budget_bands": [
                {
                    "value": band,
                    "label": label_maps["budget"][band],
                    "count": next((row["count"] for row in facets.get("budget_bands", []) if row.get("_id") == band), 0),
                }
                for band in QUOTE_BUDGET_BANDS
            ],
            "travel_windows": [
                {
                    "value": travel_key,
                    "label": label_maps["travel_window"][travel_key],
                    "count": next((row["count"] for row in facets.get("travel_windows", []) if row.get("_id") == travel_key), 0),
                }
                for travel_key in QUOTE_TRAVEL_WINDOW_FILTERS
                if travel_key != "all"
            ],
        }
    }


@router.get("/{quote_id}")
async def get_operator_quote_detail(
    quote_id: str,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    operator_profile_id = str(access_context["operator_profile"]["_id"])

    try:
        quote = await db.quote_requests.find_one({
            "_id": ObjectId(quote_id),
            "status": {"$ne": "closed"},
        })
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid quote ID") from exc

    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    return {"quote": _serialize_quote(quote, operator_profile_id=operator_profile_id)}


@router.post("/{quote_id}/respond", status_code=status.HTTP_201_CREATED)
async def respond_to_quote(
    quote_id: str,
    response: QuoteResponseCreate,
    access_context: dict = Depends(get_current_operator_access_context)
):
    db = await get_database()
    operator_profile = access_context["operator_profile"]

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
        "operator_user_id": str(access_context["principal"]["_id"]),
        "organization_id": access_context["organization"]["_id"],
        "operator_name": operator_profile.get("business_name"),
        "amount": response.amount,
        "message": response.message,
        "proposed_itinerary_snapshot": response.proposed_itinerary_snapshot.model_dump() if response.proposed_itinerary_snapshot else None,
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


@router.post("/{quote_id}/responses/{response_index}/save-itinerary", status_code=status.HTTP_201_CREATED)
async def save_response_itinerary(
    quote_id: str,
    response_index: int,
    current_user: dict = Depends(get_current_user),
):
    if current_user["user_type"] != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can save itinerary proposals")

    db = await get_database()
    try:
        quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid quote ID")

    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    if quote.get("tourist_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to save this itinerary")

    responses = quote.get("responses") or []
    if response_index < 0 or response_index >= len(responses):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote response not found")

    response_entry = responses[response_index]
    proposal = response_entry.get("proposed_itinerary_snapshot")
    if not proposal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This response does not include an itinerary proposal")

    source_template_id = proposal.get("source_template_id")
    now = datetime.now(timezone.utc)
    document = {
        "tourist_id": str(current_user["_id"]),
        "title": proposal.get("title"),
        "summary": proposal.get("summary"),
        "primary_location": proposal.get("primary_location"),
        "route_locations": proposal.get("route_locations", []),
        "duration_days": proposal.get("duration_days"),
        "trip_styles": proposal.get("trip_styles", []),
        "travelers": proposal.get("travelers"),
        "budget_band": proposal.get("budget_band"),
        "notes": proposal.get("notes"),
        "days": proposal.get("days", []),
        "status": "saved",
        "source_type": "operator_proposed",
        "source_template_ids": [source_template_id] if source_template_id else [],
        "shareable_to_quote": True,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.tourist_itineraries.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "Itinerary saved from operator response", "itinerary": document}

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
