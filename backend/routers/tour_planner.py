"""
Tour Planner Router — LLM-driven tour planning via AWS Bedrock (streaming).

Flow:
  1. POST /tour-planner/chat        — tourist sends a message; streams back Claude's reply
  2. POST /tour-planner/confirm     — tourist picks one suggested operator → add to cart

Conversation state is persisted in MongoDB `planner_sessions` so multi-turn works
across requests.  Each session is keyed by `session_id` (UUID passed by frontend).
"""

from __future__ import annotations

import json
import logging
import os
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

import boto3
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..database import get_database
from ..models.planner_quota import PlannerRewardGrantRequest
from ..routers.itineraries import search_itinerary_templates
from ..routers.auth import get_current_user
from ..utils.billing import append_planner_billing_event, build_request_fingerprint
from ..utils.billing import build_planner_impression_source_reference
from ..utils.planner_quota import consume_tourist_planner_request_quota, get_tourist_planner_quota_status, grant_tourist_planner_reward

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tour-planner", tags=["Tour Planner"])


def _require_tourist_user(current_user: dict) -> None:
    if current_user.get("user_type") != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tourists can access the planner",
        )

# ─────────────────────────────────────────────────────────────────────────────
# Bedrock client (lazy-initialised so missing creds don't crash startup)
# ─────────────────────────────────────────────────────────────────────────────

_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        key_id = settings.aws_access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        secret = settings.aws_secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        session_token = settings.aws_session_token or os.environ.get("AWS_SESSION_TOKEN")
        region = settings.aws_region

        if not key_id or not secret or key_id.startswith("YOUR_"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS Bedrock credentials are not configured. "
                       "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env.",
            )

        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": region,
            "aws_access_key_id": key_id,
            "aws_secret_access_key": secret,
        }
        if session_token:
            client_kwargs["aws_session_token"] = session_token

        _bedrock_client = boto3.client(**client_kwargs)
    return _bedrock_client


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock tool definitions
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "toolSpec": {
            "name": "extract_tour_requirements",
            "description": (
                "Extract structured travel requirements from the tourist's message. "
                "Call this once you understand where they want to go and basic trip details."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "locations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of destination names or regions mentioned",
                        },
                        "states": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Indian states or countries mentioned",
                        },
                        "travel_dates": {
                            "type": "string",
                            "description": "Travel window if mentioned (e.g. 'June 2026', 'next month')",
                        },
                        "group_size": {
                            "type": "integer",
                            "description": "Number of travelers if mentioned",
                        },
                        "budget_usd": {
                            "type": "number",
                            "description": "Approximate total budget in USD if mentioned",
                        },
                        "preferences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Activity or trip-type preferences (e.g. adventure, cultural, family)",
                        },
                        "service_mode": {
                            "type": "string",
                            "enum": ["tour", "car", "both"],
                            "description": "Type of service user wants: tour packages, car transport, or both",
                        },
                        "car_requirements": {
                            "type": "object",
                            "properties": {
                                "seats_required": {
                                    "type": "integer",
                                    "description": "Minimum number of seats required",
                                },
                                "vehicle_type": {
                                    "type": "string",
                                    "description": "Preferred vehicle type, if any",
                                },
                                "trip_type": {
                                    "type": "string",
                                    "description": "local, outstation, airport_transfer, multi_day",
                                },
                            },
                        },
                        "duration_days": {
                            "type": "integer",
                            "description": "Trip duration in days if mentioned",
                        },
                    },
                    "required": ["locations"],
                }
            },
        }
    }
]

SYSTEM_PROMPT = """You are a knowledgeable and friendly tour planning assistant for a travel platform.

Your job is to help tourists discover the right local tour operators for their trip.

Guidelines:
- Be conversational and warm. Ask clarifying questions naturally if needed.
- Once you understand the destination(s) and basic intent, call the `extract_tour_requirements` tool.
- After the tool is called, you will receive a list of real providers and, when relevant, operator-curated itinerary templates that match the request.
- Present each provider clearly with their business name, service type (tour/car), rating, and covered areas.
- If itinerary templates are returned and the user is asking for a plan or itinerary, ground your answer in those templates first instead of inventing a blind day plan.
- Be explicit when an itinerary suggestion is adapted from operator-curated templates.
- Be explicit about why each operator is suggested using `match_type` and `match_reason`.
- Treat `match_type=exact` as strongest confidence. If only `similar` matches are available, clearly say exact matches were unavailable.
- Respect budget. Prefer options with budget fit and call out when the budget may be too tight for the requested location.
- If key details are missing (dates, group size, budget), ask concise follow-up questions before finalizing recommendations.
- Let the tourist decide which operator(s) to add to their cart — never add automatically.
- Do not say "I can't add to cart" in generic terms. Instead, explicitly guide the user to use the Add to Cart button shown under each suggested operator card.
- If the user says "add this one", confirm the chosen operator name and instruct them to click that operator's Add to Cart button.
- If no operators are found for a location, say so honestly and suggest nearby alternatives if possible.
- Keep responses concise but helpful. Use bullet points for operator comparisons and finish with a clear next step."""


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get_session(db, session_id: str, user_id: str) -> dict:
    """Fetch or create a planner session document."""
    session = await db.planner_sessions.find_one(
        {"session_id": session_id, "user_id": user_id}
    )
    if not session:
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [],
            "suggested_operators": [],
            "requirements": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db.planner_sessions.insert_one(session)
    return session


async def save_session(db, session_id: str, user_id: str, messages: list,
                       suggested_operators: list, requirements: dict):
    await db.planner_sessions.update_one(
        {"session_id": session_id, "user_id": user_id},
        {
            "$set": {
                "messages": messages,
                "suggested_operators": suggested_operators,
                "requirements": requirements,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


def _normalize(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _budget_bucket(budget_usd: float | int | None) -> str | None:
    if budget_usd is None:
        return None
    if budget_usd < 700:
        return "budget"
    if budget_usd <= 1800:
        return "mid"
    return "premium"


def _operator_budget_buckets(op: dict) -> set[str]:
    text_parts = [
        op.get("description", ""),
        " ".join(op.get("specializations", [])),
        op.get("price_range", ""),
    ]
    text = _normalize(" ".join(text_parts))
    buckets: set[str] = set()
    if any(word in text for word in ["budget", "affordable", "low cost", "economy"]):
        buckets.add("budget")
    if any(word in text for word in ["luxury", "premium", "high end", "exclusive"]):
        buckets.add("premium")
    if any(word in text for word in ["mid", "standard", "value", "family"]):
        buckets.add("mid")
    if not buckets:
        buckets.add("mid")
    return buckets


def _provider_service_types(op: dict) -> set[str]:
    service_types = op.get("service_types") or ["tour"]
    norm = {_normalize(s) for s in service_types if _normalize(s)}
    return norm or {"tour"}


def _car_option_budget_bucket(option: dict) -> str:
    base_fare = option.get("base_fare")
    if base_fare is None:
        return "mid"
    try:
        fare = float(base_fare)
    except Exception:
        return "mid"
    if fare < 35:
        return "budget"
    if fare <= 120:
        return "mid"
    return "premium"


def _best_matching_car_option(
    op: dict,
    norm_locations: list[str],
    norm_states: list[str],
    seats_required: int | None,
    preferred_vehicle: str | None,
    target_budget: str | None,
) -> tuple[dict | None, float, str]:
    best_option = None
    best_score = -1.0
    best_reason = ""

    # Normalize operator's serving states for state-level fallback
    op_serving_states = [_normalize(a.get("state", "")) for a in op.get("serving_areas", []) if a.get("state")]
    norm_op_states = [s for s in op_serving_states if _normalize(s)]

    for option in op.get("car_services", []) or []:
        option_score = 0.0
        reasons = []

        coverage_areas = [_normalize(a) for a in option.get("coverage_areas", []) if _normalize(a)]
        vehicle_type = _normalize(option.get("vehicle_type", ""))
        seats = option.get("seats")

        exact_coverage_hits = [loc for loc in norm_locations if loc in coverage_areas]
        partial_coverage_hits = [
            loc for loc in norm_locations
            if any(loc in area or area in loc for area in coverage_areas)
        ]
        
        # Check if operator serves the requested state (fallback for broader coverage)
        state_match = any(state in norm_op_states for state in norm_states)

        if exact_coverage_hits:
            option_score += 48
            reasons.append(f"car coverage matches {', '.join(sorted(set(exact_coverage_hits)))}")
        elif partial_coverage_hits:
            option_score += 32
            reasons.append(f"car coverage nearby {', '.join(sorted(set(partial_coverage_hits)))}")
        elif norm_states and coverage_areas and any(state in " ".join(coverage_areas) for state in norm_states):
            option_score += 20
            reasons.append("car service available in requested state")
        elif state_match and norm_states:
            # Fallback: operator serves requested state, can likely arrange cars
            option_score += 12
            reasons.append(f"operates in {', '.join(sorted(set(norm_states)))}, can arrange transport")

        if seats_required:
            if isinstance(seats, int) and seats >= seats_required:
                option_score += 24
                reasons.append(f"supports {seats_required}+ seats")
            elif isinstance(seats, int):
                option_score -= 8  # Reduced penalty to keep car in consideration
                if seats >= seats_required - 1:
                    option_score += 12  # Boost if close to required seats

        if preferred_vehicle:
            if preferred_vehicle in vehicle_type:
                option_score += 16
                reasons.append(f"preferred vehicle: {option.get('vehicle_type')}")

        if target_budget:
            if _car_option_budget_bucket(option) == target_budget:
                option_score += 10
                reasons.append("pricing aligns with budget")

        if option_score > best_score:
            best_score = option_score
            best_option = option
            best_reason = "; ".join(reasons) if reasons else "Car service available"

    return best_option, best_score, best_reason


async def find_matching_operators(
    db,
    locations: list[str],
    states: list[str],
    budget_usd: float | int | None = None,
    preferences: list[str] | None = None,
    service_mode: str = "tour",
    car_requirements: dict | None = None,
) -> list[dict]:
    """Rank operators by exact serving-area match, then similar-location and budget fit."""
    norm_locations = [_normalize(item) for item in locations if _normalize(item)]
    norm_states = [_normalize(item) for item in states if _normalize(item)]
    norm_preferences = [_normalize(item) for item in (preferences or []) if _normalize(item)]

    if not norm_locations and not norm_states:
        return []

    location_terms = [item.strip() for item in locations if item and item.strip()]
    state_terms = [item.strip() for item in states if item and item.strip()]
    planner_query: dict = {
        "$and": [
            {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
        ]
    }

    requested_mode = _normalize(service_mode) or "tour"
    if requested_mode == "tour":
        planner_query["$and"].append({"service_types": {"$in": ["tour"]}})
    elif requested_mode == "car":
        planner_query["$and"].append({"service_types": {"$in": ["car"]}})

    area_filters = []
    for term in location_terms:
        pattern = {"$regex": re.escape(term), "$options": "i"}
        area_filters.extend([
            {"serving_areas.area_name": pattern},
            {"serving_areas.sub_locations.name": pattern},
        ])
    for term in state_terms:
        area_filters.append({"serving_areas.state": {"$regex": re.escape(term), "$options": "i"}})

    if area_filters:
        planner_query["$and"].append({"$or": area_filters})

    operators = await db.operator_profiles.find(
        planner_query,
        {
            "business_name": 1,
            "description": 1,
            "serving_areas": 1,
            "specializations": 1,
            "service_types": 1,
            "car_services": 1,
            "average_rating": 1,
            "years_of_experience": 1,
            "profile_image": 1,
        },
    ).to_list(length=150)

    if not operators:
        operators = await db.operator_profiles.find(
            {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
            {
                "business_name": 1,
                "description": 1,
                "serving_areas": 1,
                "specializations": 1,
                "service_types": 1,
                "car_services": 1,
                "average_rating": 1,
                "years_of_experience": 1,
                "profile_image": 1,
            },
        ).to_list(length=150)

    target_budget = _budget_bucket(budget_usd)
    seats_required = (car_requirements or {}).get("seats_required")
    preferred_vehicle = _normalize((car_requirements or {}).get("vehicle_type", "")) or None
    ranked: list[tuple[float, dict]] = []

    for op in operators:
        provider_services = _provider_service_types(op)
        if requested_mode == "tour" and "tour" not in provider_services:
            continue
        if requested_mode == "car" and "car" not in provider_services:
            continue

        serving_areas = op.get("serving_areas", [])
        area_names = [_normalize(a.get("area_name", "")) for a in serving_areas if a.get("area_name")]
        area_states = [_normalize(a.get("state", "")) for a in serving_areas if a.get("state")]
        sub_locations = [
            _normalize(sub.get("name", ""))
            for area in serving_areas
            for sub in area.get("sub_locations", [])
            if sub.get("name")
        ]
        candidates = area_names + sub_locations

        exact_hits = [loc for loc in norm_locations if loc in area_names or loc in sub_locations]
        partial_hits = [
            loc for loc in norm_locations
            if any(loc in cand or cand in loc for cand in candidates)
        ]
        state_hits = [state for state in norm_states if state in area_states]

        best_similarity = 0.0
        for loc in norm_locations:
            for cand in candidates:
                best_similarity = max(best_similarity, SequenceMatcher(None, loc, cand).ratio())

        budget_fit = False
        if target_budget:
            budget_fit = target_budget in _operator_budget_buckets(op)

        # Enhanced preference/specialization matching for tours
        preference_fit_count = 0
        specialization_fit_count = 0
        if norm_preferences:
            norm_specializations = [_normalize(s) for s in op.get("specializations", []) if _normalize(s)]
            # Direct specialization match (weighted higher)
            specialization_fit_count = sum(1 for pref in norm_preferences if pref in norm_specializations)
            
            # Broader search in description + specializations
            search_blob = _normalize(
                " ".join(
                    [op.get("description", "")] +
                    op.get("specializations", []) +
                    [" ".join(area_names), " ".join(sub_locations)]
                )
            )
            preference_fit_count = sum(1 for pref in norm_preferences if pref and pref in search_blob)

        rating = float(op.get("average_rating", 0) or 0)

        score = 0.0
        match_type = "fallback"
        match_reason = "Suggested by rating and related preferences"
        
        # Build list of matched specializations for better reasoning
        matched_specializations = []
        if specialization_fit_count > 0:
            norm_preferences_list = [_normalize(p) for p in norm_preferences if _normalize(p)]
            norm_specializations = [_normalize(s) for s in op.get("specializations", []) if _normalize(s)]
            matched_specializations = [s for s in norm_specializations if s in norm_preferences_list]

        if exact_hits:
            score += 100
            match_type = "exact"
            match_reason = f"Exact serving-area match for {', '.join(sorted(set(exact_hits)))}"
            if matched_specializations:
                match_reason += f" • Specializes in {', '.join(matched_specializations)}"
        elif partial_hits:
            score += 70
            match_type = "similar"
            match_reason = f"Similar area name match for {', '.join(sorted(set(partial_hits)))}"
            if matched_specializations:
                match_reason += f" • {', '.join(matched_specializations)} tours"
        elif state_hits:
            score += 55
            match_type = "similar"
            match_reason = f"Serves same state: {', '.join(sorted(set(state_hits)))}"
            if matched_specializations:
                match_reason += f" • Offers {', '.join(matched_specializations)}"
        elif best_similarity >= 0.72:
            score += 48
            match_type = "similar"
            match_reason = "Closest available area by location similarity"
            if matched_specializations:
                match_reason += f" • {', '.join(matched_specializations)} tours available"
        elif matched_specializations:
            # Fallback improved with strong specialization match
            match_reason = f"Expert in {', '.join(matched_specializations)}"

        if budget_fit:
            score += 16
            match_reason += " with matching budget"
        
        # Enhanced preference scoring: specialization matches weighted higher
        if specialization_fit_count:
            score += min(specialization_fit_count * 12, 28)  # Increased weight for specializations
            if preference_fit_count > specialization_fit_count:
                score += min((preference_fit_count - specialization_fit_count) * 4, 12)
        elif preference_fit_count:
            score += min(preference_fit_count * 6, 18)
        
        score += min(rating, 5.0)

        recommended_service = "tour"
        car_option = None
        car_reason = ""
        if "car" in provider_services:
            car_option, car_score, car_reason = _best_matching_car_option(
                op,
                norm_locations,
                norm_states,
                seats_required=seats_required,
                preferred_vehicle=preferred_vehicle,
                target_budget=target_budget,
            )

            if requested_mode == "car":
                # Relax threshold for car-only searches: allow partial matches if score >= 5
                # Also add fallback boost if operator is in same state
                min_car_score = 5
                if car_option and car_score >= min_car_score:
                    recommended_service = "car"
                    score = car_score + min(rating, 5.0)
                    match_type = "exact" if car_score >= 48 else ("similar" if car_score >= 20 else "nearby")
                    match_reason = car_reason or "Car service available"
                elif not car_option:
                    continue
                else:
                    # If score is borderline (3-5) and operator is in right state, still consider
                    op_states = [_normalize(a.get("state", "")) for a in op.get("serving_areas", []) if a.get("state")]
                    if any(state in op_states for state in norm_states) and car_score >= 2:
                        recommended_service = "car"
                        score = car_score + 3 + min(rating, 5.0)  # Small boost for being in-state
                        match_type = "nearby"
                        match_reason = car_reason + " (in-state option)" if car_reason else "In-state car service available"
                    else:
                        continue
            elif requested_mode == "both":
                if car_option and car_score > score + 4:
                    recommended_service = "car"
                    score = car_score + min(rating, 5.0)
                    match_type = "exact" if car_score >= 48 else "similar"
                    match_reason = car_reason or match_reason
                else:
                    recommended_service = "tour"

        if requested_mode == "both" and recommended_service == "tour" and "tour" not in provider_services:
            continue

        # Improved fallback filtering for tours
        if match_type == "fallback":
            # Allow lower fallback scores for tours if there are strong preference/specialization matches
            min_fallback_score = 8 if specialization_fit_count > 0 else 12
            if score < min_fallback_score:
                continue

        areas = [area.get("area_name", "") for area in serving_areas if area.get("area_name")]
        area_details = []
        for area in serving_areas[:5]:
            coords = area.get("coordinates") or {}
            latitude = coords.get("latitude")
            longitude = coords.get("longitude")
            if latitude is None or longitude is None:
                first_sub_with_coords = next(
                    (
                        sub for sub in area.get("sub_locations", [])
                        if (sub.get("coordinates") or {}).get("latitude") is not None
                        and (sub.get("coordinates") or {}).get("longitude") is not None
                    ),
                    None,
                )
                if first_sub_with_coords:
                    sub_coords = first_sub_with_coords.get("coordinates") or {}
                    latitude = sub_coords.get("latitude")
                    longitude = sub_coords.get("longitude")
            area_details.append({
                "area_name": area.get("area_name", ""),
                "state": area.get("state", ""),
                "country": area.get("country", ""),
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                } if latitude is not None and longitude is not None else None,
            })

        ranked.append((score, {
            "id": str(op.get("_id")),
            "business_name": op.get("business_name", ""),
            "description": op.get("description", ""),
            "average_rating": rating,
            "total_reviews": op.get("total_reviews", 0),
            "serving_areas": areas[:5],
            "serving_area_details": area_details,
            "price_range": op.get("price_range", ""),
            "user_id": str(op.get("user_id", "")),
            "service_types": sorted(list(provider_services)),
            "recommended_service": recommended_service,
            "car_option": {
                "vehicle_type": car_option.get("vehicle_type"),
                "vehicle_label": car_option.get("vehicle_label"),
                "seats": car_option.get("seats"),
                "luggage_capacity": car_option.get("luggage_capacity"),
                "pricing_model": car_option.get("pricing_model"),
                "base_fare": car_option.get("base_fare"),
                "fare_per_km": car_option.get("fare_per_km"),
                "coverage_areas": car_option.get("coverage_areas", []),
            } if car_option else None,
            "match_type": match_type,
            "match_reason": match_reason,
            "budget_fit": budget_fit,
            "preference_fit_count": preference_fit_count,
            "score": round(score, 2),
        }))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:6]]


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str
    service_mode: str | None = None


class ConfirmRequest(BaseModel):
    session_id: str
    operator_id: str  # id from suggested_operators


def _quota_error_detail(result: dict) -> dict:
    return {
        "message": "Planner request limit reached",
        "reason": result.get("reason") or "quota_exhausted",
        "quota": result.get("quota") or {},
    }


@router.get("/quota")
async def get_planner_quota(current_user: dict = Depends(get_current_user)):
    _require_tourist_user(current_user)
    db = await get_database()
    return await get_tourist_planner_quota_status(db, user_id=str(current_user["_id"]))


@router.post("/quota/rewards/grant")
async def grant_planner_reward(
    payload: PlannerRewardGrantRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_tourist_user(current_user)
    db = await get_database()
    result = await grant_tourist_planner_reward(
        db,
        user_id=str(current_user["_id"]),
        reward_id=payload.reward_id,
        reward_type=payload.reward_type,
    )
    if not result.get("granted"):
        if result.get("reason") == "reward_not_verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reward has not been verified server-side",
            )
        if result.get("reason") == "duplicate_reward":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Reward already consumed",
                    "quota": result.get("quota") or {},
                },
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward grant failed")

    return {
        "message": "Planner reward granted",
        "quota": result.get("quota") or {},
        "reward_id": payload.reward_id,
        "reward_type": payload.reward_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Streaming chat endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def planner_chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Stream a tour planning conversation turn using AWS Bedrock.
    Returns SSE-style text/event-stream.
    """
    _require_tourist_user(current_user)
    db = await get_database()
    user_id = str(current_user["_id"])

    quota_result = await consume_tourist_planner_request_quota(
        db,
        user_id=user_id,
        session_id=req.session_id,
    )
    if not quota_result.get("allowed"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_quota_error_detail(quota_result),
        )

    bedrock = get_bedrock_client()

    session = await get_session(db, req.session_id, user_id)
    messages = session.get("messages", [])
    suggested_operators = session.get("suggested_operators", [])
    requirements = session.get("requirements", {})

    # Append tourist's new message
    messages.append({"role": "user", "content": [{"text": req.message}]})

    async def stream_response() -> AsyncGenerator[str, None]:
        nonlocal messages, suggested_operators, requirements

        full_assistant_text = ""
        tool_use_block = None
        tool_use_id = None

        try:
            response = bedrock.converse_stream(
                modelId=settings.bedrock_model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                toolConfig={"tools": TOOLS},
                inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
            )

            for event in response["stream"]:

                # ── Streaming text delta ────────────────────────────────────
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        chunk = delta["text"]
                        full_assistant_text += chunk
                        yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"

                    elif "toolUse" in delta:
                        # accumulate tool input JSON
                        if tool_use_block is None:
                            tool_use_block = ""
                        tool_use_block += delta["toolUse"].get("input", "")

                # ── Tool use start (capture id) ─────────────────────────────
                if "contentBlockStart" in event:
                    start = event["contentBlockStart"].get("start", {})
                    if "toolUse" in start:
                        tool_use_id = start["toolUse"]["toolUseId"]
                        tool_use_block = ""

                # ── Message stop — handle tool call ────────────────────────
                if "messageStop" in event:
                    stop_reason = event["messageStop"].get("stopReason")

                    if stop_reason == "tool_use" and tool_use_id:
                        yield f"data: {json.dumps({'type': 'status', 'text': '🔍 Searching for operators and itinerary ideas...'})}\n\n"

                        # Parse extracted requirements
                        try:
                            extracted = json.loads(tool_use_block) if tool_use_block else {}
                        except json.JSONDecodeError:
                            extracted = {}

                        requirements.update(extracted)
                        locations = extracted.get("locations", [])
                        states = extracted.get("states", [])
                        budget_usd = extracted.get("budget_usd")
                        preferences = extracted.get("preferences", [])
                        service_mode = extracted.get("service_mode") or req.service_mode or "tour"
                        car_requirements = extracted.get("car_requirements") or {}
                        itinerary_matches = await search_itinerary_templates(
                            db,
                            area_name=locations[0] if locations else None,
                            state=states[0] if states else None,
                            country=None,
                            duration_days=extracted.get("duration_days"),
                            trip_styles=preferences,
                            traveler_types=[],
                            budget_band=_budget_bucket(budget_usd),
                            limit=5,
                        )

                        # Query real operators from DB
                        matched = await find_matching_operators(
                            db,
                            locations,
                            states,
                            budget_usd=budget_usd,
                            preferences=preferences,
                            service_mode=service_mode,
                            car_requirements=car_requirements,
                        )
                        suggested_operators = matched
                        for op in suggested_operators:
                            await append_planner_billing_event(
                                db,
                                operator_profile_id=op["id"],
                                event_type="impression",
                                source_reference_type="planner_session",
                                source_reference_id=build_planner_impression_source_reference(
                                    session_id=req.session_id,
                                    operator_profile_id=op["id"],
                                ),
                                anonymous_session_id=req.session_id,
                                request_fingerprint=build_request_fingerprint(
                                    session_id=req.session_id,
                                    request_id=None,
                                    client_host=None,
                                    user_agent=None,
                                ),
                                outcome_reason="planner_recommendation_served",
                                metadata={
                                    "match_type": op.get("match_type"),
                                    "recommended_service": op.get("recommended_service"),
                                    "budget_fit": op.get("budget_fit", False),
                                    "score": op.get("score", 0),
                                    "locations": locations,
                                    "states": states,
                                },
                            )
                        exact_count = sum(1 for op in matched if op.get("match_type") == "exact")
                        similar_count = sum(1 for op in matched if op.get("match_type") == "similar")
                        budget_fit_count = sum(1 for op in matched if op.get("budget_fit"))

                        # Build tool result for Bedrock
                        tool_result_content = json.dumps({
                            "operators_found": len(matched),
                            "exact_matches": exact_count,
                            "similar_matches": similar_count,
                            "budget_fit_matches": budget_fit_count,
                            "operators": [
                                {
                                    "id": op["id"],
                                    "business_name": op["business_name"],
                                    "serving_areas": op["serving_areas"],
                                    "serving_area_details": op.get("serving_area_details", []),
                                    "average_rating": op["average_rating"],
                                    "total_reviews": op["total_reviews"],
                                    "price_range": op.get("price_range", ""),
                                    "service_types": op.get("service_types", ["tour"]),
                                    "recommended_service": op.get("recommended_service", "tour"),
                                    "car_option": op.get("car_option"),
                                    "match_type": op.get("match_type", "similar"),
                                    "match_reason": op.get("match_reason", ""),
                                    "budget_fit": op.get("budget_fit", False),
                                    "preference_fit_count": op.get("preference_fit_count", 0),
                                    "score": op.get("score", 0),
                                }
                                for op in matched
                            ],
                            "itinerary_templates_found": len(itinerary_matches),
                            "itinerary_templates": [
                                {
                                    "id": item["_id"],
                                    "title": item.get("title"),
                                    "summary": item.get("summary"),
                                    "operator_name": item.get("operator_name"),
                                    "primary_location": item.get("primary_location"),
                                    "duration_days": item.get("duration_days"),
                                    "trip_styles": item.get("trip_styles", []),
                                    "budget_band": item.get("budget_band"),
                                    "days": [
                                        {
                                            "day_number": day.get("day_number"),
                                            "title": day.get("title"),
                                            "summary": day.get("summary"),
                                            "highlights": day.get("highlights", []),
                                            "overnight_location": day.get("overnight_location"),
                                        }
                                        for day in (item.get("days") or [])[: min(5, extracted.get("duration_days") or 5)]
                                    ],
                                    "score": item.get("score", 0),
                                }
                                for item in itinerary_matches
                            ],
                        })

                        # Add assistant turn (tool use) + tool result to messages
                        messages.append({
                            "role": "assistant",
                            "content": [
                                {
                                    "toolUse": {
                                        "toolUseId": tool_use_id,
                                        "name": "extract_tour_requirements",
                                        "input": extracted,
                                    }
                                }
                            ],
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": {
                                        "toolUseId": tool_use_id,
                                        "content": [{"text": tool_result_content}],
                                    }
                                }
                            ],
                        })

                        # Second Bedrock turn to render the plan
                        response2 = bedrock.converse_stream(
                            modelId=settings.bedrock_model_id,
                            system=[{"text": SYSTEM_PROMPT}],
                            messages=messages,
                            toolConfig={"tools": TOOLS},
                            inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
                        )

                        second_text = ""
                        for ev2 in response2["stream"]:
                            if "contentBlockDelta" in ev2:
                                d = ev2["contentBlockDelta"].get("delta", {})
                                if "text" in d:
                                    second_text += d["text"]
                                    yield f"data: {json.dumps({'type': 'text', 'text': d['text']})}\n\n"

                        # Append assistant's final reply
                        messages.append({
                            "role": "assistant",
                            "content": [{"text": second_text}],
                        })

                        # Emit suggested operators to frontend
                        yield f"data: {json.dumps({'type': 'operators', 'operators': suggested_operators})}\n\n"
                        yield f"data: {json.dumps({'type': 'itineraries', 'itineraries': itinerary_matches})}\n\n"

                    elif stop_reason == "end_turn" and full_assistant_text:
                        messages.append({
                            "role": "assistant",
                            "content": [{"text": full_assistant_text}],
                        })

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except bedrock.exceptions.ValidationException as exc:
            logger.error("Bedrock validation error: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"
        except Exception as exc:
            logger.exception("Bedrock streaming error")
            yield f"data: {json.dumps({'type': 'error', 'text': 'Something went wrong. Please try again.'})}\n\n"
        finally:
            # Always persist session
            await save_session(db, req.session_id, user_id, messages, suggested_operators, requirements)

    return StreamingResponse(stream_response(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────────────────────────────
# Confirm — add chosen operator to cart
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/confirm")
async def planner_confirm(
    req: ConfirmRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Tourist picks one suggested operator — add it to their cart (quotes store).
    """
    _require_tourist_user(current_user)
    db = await get_database()
    user_id = str(current_user["_id"])

    session = await db.planner_sessions.find_one(
        {"session_id": req.session_id, "user_id": user_id}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find operator in suggestions
    suggested = session.get("suggested_operators", [])
    operator = next((op for op in suggested if op["id"] == req.operator_id), None)
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not in this session's suggestions")

    requirements = session.get("requirements", {})

    # Build a cart item in the quotes collection so existing cart UI works
    cart_item = {
        "tourist_id": user_id,
        "operator_id": req.operator_id,
        "operator_name": operator["business_name"],
        "serving_areas": operator["serving_areas"],
        "status": "cart",
        "source": "tour_planner",
        "locations": [
            {"name": loc} for loc in requirements.get("locations", operator["serving_areas"][:1])
        ],
        "travel_window": requirements.get("travel_dates", ""),
        "travelers": requirements.get("group_size"),
        "budget": requirements.get("budget_usd"),
        "preferences": requirements.get("preferences", []),
        "notes": f"Added via Tour Planner — session {req.session_id}",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await db.quotes.insert_one(cart_item)

    await append_planner_billing_event(
        db,
        operator_profile_id=req.operator_id,
        event_type="intent_click",
        source_reference_type="planner_session",
        source_reference_id=f"{req.session_id}:{req.operator_id}:confirm",
        anonymous_session_id=req.session_id,
        request_fingerprint=build_request_fingerprint(
            session_id=req.session_id,
            request_id=str(result.inserted_id),
            client_host=None,
            user_agent=None,
        ),
        outcome_reason="planner_quote_intent_created",
        metadata={
            "quote_id": str(result.inserted_id),
            "operator_name": operator["business_name"],
            "match_type": operator.get("match_type"),
            "recommended_service": operator.get("recommended_service"),
        },
    )

    return {
        "message": f"{operator['business_name']} added to your cart.",
        "quote_id": str(result.inserted_id),
        "operator": operator,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Get session history (for page reload)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/session/{session_id}")
async def get_planner_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    _require_tourist_user(current_user)
    db = await get_database()
    user_id = str(current_user["_id"])
    session = await db.planner_sessions.find_one(
        {"session_id": session_id, "user_id": user_id}
    )
    if not session:
        return {"messages": [], "suggested_operators": [], "requirements": {}}

    # Convert messages to frontend-friendly format
    readable = []
    for m in session.get("messages", []):
        role = m.get("role")
        content = m.get("content", [])
        text = " ".join(
            c.get("text", "") for c in content if isinstance(c, dict) and "text" in c
        )
        if text.strip():
            readable.append({"role": role, "text": text})

    return {
        "messages": readable,
        "suggested_operators": session.get("suggested_operators", []),
        "requirements": session.get("requirements", {}),
    }


@router.get("/session/{session_id}/itineraries")
async def get_planner_itineraries(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    _require_tourist_user(current_user)
    db = await get_database()
    user_id = str(current_user["_id"])
    session = await db.planner_sessions.find_one({"session_id": session_id, "user_id": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    requirements = session.get("requirements", {}) or {}
    locations = requirements.get("locations") or []
    states = requirements.get("states") or []
    preferences = requirements.get("preferences") or []
    duration_days = requirements.get("duration_days")
    budget_usd = requirements.get("budget_usd")

    budget_band = None
    if isinstance(budget_usd, (int, float)):
        budget_band = _budget_bucket(budget_usd)

    itineraries = await search_itinerary_templates(
        db,
        area_name=locations[0] if locations else None,
        state=states[0] if states else None,
        country=None,
        duration_days=duration_days,
        trip_styles=preferences,
        traveler_types=[],
        budget_band=budget_band,
    )

    return {
        "itineraries": itineraries,
        "count": len(itineraries),
        "requirements": requirements,
    }
