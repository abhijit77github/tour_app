from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_database
from ..models.itinerary import (
    ItinerarySearchQuery,
    OperatorItineraryTemplateCreate,
    OperatorItineraryTemplateUpdate,
    TouristItineraryCreate,
    TouristItineraryUpdate,
)
from ..routers.auth import get_current_operator_access_context, get_current_user
from ..utils.billing import append_planner_billing_event, build_request_fingerprint
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])


def _normalize(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def _serialize_doc(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def _sanitize_text_search(value: Optional[str]) -> str | None:
    cleaned = " ".join((value or "").strip().split())
    if not cleaned:
        return None

    cleaned = re.sub(r"[^\w\s\-']", " ", cleaned, flags=re.UNICODE)
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def _build_title_search_pattern(value: Optional[str]) -> str | None:
    cleaned = _sanitize_text_search(value)
    if not cleaned:
        return None

    tokens = [re.escape(token) for token in cleaned.split() if token]
    if not tokens:
        return None
    return r"\s+".join(tokens)


def _location_matches_scope(scope: dict, target: dict) -> bool:
    if scope.get("area_name") and _normalize(target.get("area_name")) != _normalize(scope.get("area_name")):
        return False
    if scope.get("state") and _normalize(target.get("state")) != _normalize(scope.get("state")):
        return False
    if scope.get("country") and _normalize(target.get("country")) != _normalize(scope.get("country")):
        return False
    return True


def _operator_supports_location(profile: dict, location: dict) -> bool:
    return any(_location_matches_scope(location, area) for area in profile.get("serving_areas", []))


def _serialize_search_result(template: dict, score: float) -> dict:
    doc = _serialize_doc(template)
    doc["score"] = round(score, 2)
    return doc


async def search_itinerary_templates(
    db,
    *,
    area_name: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    duration_days: Optional[int] = None,
    trip_styles: Optional[list[str]] = None,
    traveler_types: Optional[list[str]] = None,
    budget_band: Optional[str] = None,
    limit: int = 8,
) -> list[dict]:
    query = {"status": "published"}
    if area_name:
        query["primary_location.area_name"] = {"$regex": area_name, "$options": "i"}
    if state:
        query["primary_location.state"] = {"$regex": state, "$options": "i"}
    if country:
        query["primary_location.country"] = {"$regex": country, "$options": "i"}

    templates = await db.operator_itinerary_templates.find(query).to_list(100)
    trip_styles = [_normalize(item) for item in (trip_styles or []) if _normalize(item)]
    traveler_types = [_normalize(item) for item in (traveler_types or []) if _normalize(item)]
    target_area = _normalize(area_name)
    target_state = _normalize(state)
    target_country = _normalize(country)

    ranked = []
    for template in templates:
        score = 0.0
        primary = template.get("primary_location") or {}
        route_locations = template.get("route_locations") or []
        route_names = {_normalize(loc.get("area_name")) for loc in route_locations}
        route_states = {_normalize(loc.get("state")) for loc in route_locations}
        route_countries = {_normalize(loc.get("country")) for loc in route_locations}

        if target_area:
            if _normalize(primary.get("area_name")) == target_area:
                score += 52
            elif target_area in route_names:
                score += 32

        if target_state:
            if _normalize(primary.get("state")) == target_state:
                score += 18
            elif target_state in route_states:
                score += 10

        if target_country:
            if _normalize(primary.get("country")) == target_country:
                score += 12
            elif target_country in route_countries:
                score += 6

        if duration_days:
            template_duration = template.get("duration_days") or 0
            if template_duration == duration_days:
                score += 24
            elif abs(template_duration - duration_days) == 1:
                score += 14
            elif abs(template_duration - duration_days) <= 2:
                score += 8

        template_styles = {_normalize(item) for item in template.get("trip_styles", [])}
        template_travelers = {_normalize(item) for item in template.get("traveler_types", [])}
        score += 8 * len(template_styles.intersection(trip_styles))
        score += 6 * len(template_travelers.intersection(traveler_types))

        if budget_band and template.get("budget_band") == budget_band:
            score += 8

        if score > 0:
            ranked.append((score, template))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [_serialize_search_result(template, score) for score, template in ranked[:limit]]


async def _get_tourist_or_403(current_user: dict) -> str:
    if current_user.get("user_type") != "tourist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only tourists can manage personal itineraries")
    return str(current_user["_id"])


@router.get("/search")
async def get_matching_itineraries(
    area_name: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    duration_days: Optional[int] = Query(default=None, ge=1, le=30),
    trip_styles: Optional[str] = None,
    traveler_types: Optional[str] = None,
    budget_band: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    _ = current_user
    trip_style_items = [item.strip() for item in (trip_styles or "").split(",") if item.strip()]
    traveler_type_items = [item.strip() for item in (traveler_types or "").split(",") if item.strip()]
    results = await search_itinerary_templates(
        db,
        area_name=area_name,
        state=state,
        country=country,
        duration_days=duration_days,
        trip_styles=trip_style_items,
        traveler_types=traveler_type_items,
        budget_band=budget_band,
    )
    return {"itineraries": results, "count": len(results)}


@router.get("/operator/templates")
async def list_operator_templates(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=80),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|archived)$"),
    budget_band: str | None = Query(default=None, pattern="^(budget|mid|premium)$"),
    area_name: str | None = Query(default=None, max_length=80),
    state: str | None = Query(default=None, max_length=80),
    country: str | None = Query(default=None, max_length=80),
    duration_days: int | None = Query(default=None, ge=1, le=30),
    trip_style: str | None = Query(default=None, min_length=1, max_length=40),
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    base_query = {"operator_profile_id": str(profile["_id"])}
    title_search_pattern = _build_title_search_pattern(search)
    if title_search_pattern:
        base_query["title"] = {"$regex": title_search_pattern, "$options": "i"}
    if status_filter:
        base_query["status"] = status_filter
    if budget_band:
        base_query["budget_band"] = budget_band
    if area_name:
        base_query["primary_location.area_name"] = area_name.strip()
    if state:
        base_query["primary_location.state"] = state.strip()
    if country:
        base_query["primary_location.country"] = country.strip()
    if duration_days:
        base_query["duration_days"] = duration_days
    if trip_style:
        base_query["trip_styles"] = _sanitize_text_search(trip_style)

    total_items = await db.operator_itinerary_templates.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        try:
            cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id, field_name="updated_at")
        ]
    docs = []
    rows = await db.operator_itinerary_templates.find(effective_query).sort([("updated_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_row["updated_at"], object_id=last_row["_id"])
    for doc in rows:
        docs.append(_serialize_doc(doc))
    return {
        "templates": docs,
        "count": len(docs),
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.get("/operator/templates/filter-options")
async def get_operator_template_filter_options(
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    base_match = {"operator_profile_id": str(profile["_id"])}

    def _count_map(rows: list[dict]) -> dict[str, int]:
        return {str(row.get("_id")): row.get("count", 0) for row in rows if row.get("_id") not in (None, "")}

    status_rows = await db.operator_itinerary_templates.aggregate([
        {"$match": base_match},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]).to_list(length=None)
    budget_rows = await db.operator_itinerary_templates.aggregate([
        {"$match": {**base_match, "budget_band": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$budget_band", "count": {"$sum": 1}}},
    ]).to_list(length=None)
    duration_rows = await db.operator_itinerary_templates.aggregate([
        {"$match": base_match},
        {"$group": {"_id": "$duration_days", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=None)
    trip_style_rows = await db.operator_itinerary_templates.aggregate([
        {"$match": base_match},
        {"$unwind": "$trip_styles"},
        {"$match": {"trip_styles": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$trip_styles", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]).to_list(length=None)
    location_rows = await db.operator_itinerary_templates.aggregate([
        {"$match": base_match},
        {
            "$group": {
                "_id": {
                    "area_name": "$primary_location.area_name",
                    "state": "$primary_location.state",
                    "country": "$primary_location.country",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.area_name": 1, "_id.state": 1, "_id.country": 1}},
    ]).to_list(length=None)

    status_counts = _count_map(status_rows)
    budget_counts = _count_map(budget_rows)

    return {
        "filters": {
            "status": [
                {"value": value, "label": label, "count": status_counts.get(value, 0)}
                for value, label in (("draft", "Draft"), ("published", "Published"), ("archived", "Archived"))
                if status_counts.get(value, 0) > 0
            ],
            "budget": [
                {"value": value, "label": label, "count": budget_counts.get(value, 0)}
                for value, label in (("budget", "Budget"), ("mid", "Mid"), ("premium", "Premium"))
                if budget_counts.get(value, 0) > 0
            ],
            "duration": [
                {
                    "value": str(row["_id"]),
                    "label": f"{row['_id']} day" if row["_id"] == 1 else f"{row['_id']} days",
                    "count": row["count"],
                }
                for row in duration_rows
                if row.get("_id") is not None
            ],
            "trip_style": [
                {
                    "value": str(row["_id"]),
                    "label": str(row["_id"]).strip(),
                    "count": row["count"],
                }
                for row in trip_style_rows
                if row.get("_id")
            ],
            "location": [
                {
                    "value": f"{location.get('area_name') or ''}||{location.get('state') or ''}||{location.get('country') or ''}",
                    "label": ", ".join(part for part in (location.get("area_name"), location.get("state"), location.get("country")) if part),
                    "count": row.get("count", 0),
                }
                for row in location_rows
                for location in [row.get("_id") or {}]
                if location.get("area_name")
            ],
        }
    }


@router.post("/operator/templates", status_code=status.HTTP_201_CREATED)
async def create_operator_template(
    payload: OperatorItineraryTemplateCreate,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    data = payload.model_dump()
    if not _operator_supports_location(profile, data["primary_location"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Primary itinerary location must be part of your serving areas")

    now = datetime.now(timezone.utc)
    document = {
        **data,
        "operator_profile_id": str(profile["_id"]),
        "operator_user_id": str(access_context["principal"]["_id"]),
        "organization_id": access_context["organization"]["_id"],
        "operator_name": profile.get("business_name"),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.operator_itinerary_templates.insert_one(document)
    document["_id"] = result.inserted_id
    return {"message": "Itinerary template created", "template": _serialize_doc(document)}


@router.patch("/operator/templates/{template_id}")
async def update_operator_template(
    template_id: str,
    payload: OperatorItineraryTemplateUpdate,
    access_context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    profile = access_context["operator_profile"]
    try:
        existing = await db.operator_itinerary_templates.find_one({"_id": ObjectId(template_id), "operator_profile_id": str(profile["_id"])})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid template ID") from exc
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    if "primary_location" in update_data and not _operator_supports_location(profile, update_data["primary_location"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Primary itinerary location must be part of your serving areas")
    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.operator_itinerary_templates.update_one({"_id": existing["_id"]}, {"$set": update_data})
    updated = await db.operator_itinerary_templates.find_one({"_id": existing["_id"]})
    return {"message": "Itinerary template updated", "template": _serialize_doc(updated)}


@router.delete("/operator/templates/{template_id}")
async def delete_operator_template(template_id: str, access_context: dict = Depends(get_current_operator_access_context)):
    db = await get_database()
    profile = access_context["operator_profile"]
    try:
        result = await db.operator_itinerary_templates.delete_one({"_id": ObjectId(template_id), "operator_profile_id": str(profile["_id"])})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid template ID") from exc
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return {"message": "Itinerary template deleted"}


@router.get("/my")
async def list_my_itineraries(current_user: dict = Depends(get_current_user)):
    db = await get_database()
    tourist_id = await _get_tourist_or_403(current_user)
    docs = []
    cursor = db.tourist_itineraries.find({"tourist_id": tourist_id}).sort("updated_at", -1)
    async for doc in cursor:
        docs.append(_serialize_doc(doc))
    return {"itineraries": docs, "count": len(docs)}


@router.post("/my", status_code=status.HTTP_201_CREATED)
async def create_tourist_itinerary(
    payload: TouristItineraryCreate,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    tourist_id = await _get_tourist_or_403(current_user)
    now = datetime.now(timezone.utc)
    document = {
        **payload.model_dump(),
        "tourist_id": tourist_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.tourist_itineraries.insert_one(document)
    document["_id"] = result.inserted_id
    return {"message": "Itinerary saved", "itinerary": _serialize_doc(document)}


@router.post("/my/from-template/{template_id}", status_code=status.HTTP_201_CREATED)
async def create_tourist_itinerary_from_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    tourist_id = await _get_tourist_or_403(current_user)
    try:
        template = await db.operator_itinerary_templates.find_one({"_id": ObjectId(template_id), "status": "published"})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid template ID") from exc
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    now = datetime.now(timezone.utc)
    document = {
        "tourist_id": tourist_id,
        "title": template.get("title"),
        "summary": template.get("summary"),
        "primary_location": template.get("primary_location"),
        "route_locations": template.get("route_locations", []),
        "duration_days": template.get("duration_days"),
        "trip_styles": template.get("trip_styles", []),
        "travelers": None,
        "budget_band": template.get("budget_band"),
        "notes": template.get("notes_for_planner"),
        "days": template.get("days", []),
        "status": "saved",
        "source_type": "template_based",
        "source_template_ids": [str(template["_id"])],
        "shareable_to_quote": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.tourist_itineraries.insert_one(document)
    document["_id"] = result.inserted_id

    operator_profile_id = template.get("operator_profile_id")
    if operator_profile_id:
        await append_planner_billing_event(
            db,
            operator_profile_id=operator_profile_id,
            event_type="conversion",
            source_reference_type="itinerary_template",
            source_reference_id=str(document["_id"]),
            anonymous_session_id=tourist_id,
            request_fingerprint=build_request_fingerprint(
                session_id=tourist_id,
                request_id=str(document["_id"]),
                client_host=None,
                user_agent=None,
            ),
            outcome_reason="template_itinerary_saved",
            metadata={
                "template_id": str(template["_id"]),
                "template_title": template.get("title"),
                "source_type": "template_based",
                "duration_days": template.get("duration_days"),
            },
        )

    return {"message": "Itinerary created from template", "itinerary": _serialize_doc(document)}


@router.patch("/my/{itinerary_id}")
async def update_tourist_itinerary(
    itinerary_id: str,
    payload: TouristItineraryUpdate,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    tourist_id = await _get_tourist_or_403(current_user)
    try:
        existing = await db.tourist_itineraries.find_one({"_id": ObjectId(itinerary_id), "tourist_id": tourist_id})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid itinerary ID") from exc
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.tourist_itineraries.update_one({"_id": existing["_id"]}, {"$set": update_data})
    updated = await db.tourist_itineraries.find_one({"_id": existing["_id"]})
    return {"message": "Itinerary updated", "itinerary": _serialize_doc(updated)}


@router.delete("/my/{itinerary_id}")
async def delete_tourist_itinerary(itinerary_id: str, current_user: dict = Depends(get_current_user)):
    db = await get_database()
    tourist_id = await _get_tourist_or_403(current_user)
    try:
        result = await db.tourist_itineraries.delete_one({"_id": ObjectId(itinerary_id), "tourist_id": tourist_id})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid itinerary ID") from exc
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return {"message": "Itinerary deleted"}