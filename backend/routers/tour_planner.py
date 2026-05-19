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
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tour-planner", tags=["Tour Planner"])

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
- After the tool is called, you will receive a list of real operators who serve those areas.
- Present each operator clearly with their business name, rating, and the locations they cover.
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


async def find_matching_operators(
    db,
    locations: list[str],
    states: list[str],
    budget_usd: float | int | None = None,
    preferences: list[str] | None = None,
) -> list[dict]:
    """Rank operators by exact serving-area match, then similar-location and budget fit."""
    norm_locations = [_normalize(item) for item in locations if _normalize(item)]
    norm_states = [_normalize(item) for item in states if _normalize(item)]
    norm_preferences = [_normalize(item) for item in (preferences or []) if _normalize(item)]

    if not norm_locations and not norm_states:
        return []

    operators = await db.operator_profiles.find(
        {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}
    ).to_list(length=300)

    target_budget = _budget_bucket(budget_usd)
    ranked: list[tuple[float, dict]] = []

    for op in operators:
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

        preference_fit_count = 0
        if norm_preferences:
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

        if exact_hits:
            score += 100
            match_type = "exact"
            match_reason = f"Exact serving-area match for {', '.join(sorted(set(exact_hits)))}"
        elif partial_hits:
            score += 70
            match_type = "similar"
            match_reason = f"Similar area name match for {', '.join(sorted(set(partial_hits)))}"
        elif state_hits:
            score += 55
            match_type = "similar"
            match_reason = f"Serves same state: {', '.join(sorted(set(state_hits)))}"
        elif best_similarity >= 0.72:
            score += 48
            match_type = "similar"
            match_reason = "Closest available area by location similarity"

        if budget_fit:
            score += 16
            match_reason += " with matching budget"
        if preference_fit_count:
            score += min(preference_fit_count * 6, 18)
        score += min(rating, 5.0)

        if match_type == "fallback" and score < 12:
            continue

        areas = [area.get("area_name", "") for area in serving_areas if area.get("area_name")]
        area_details = []
        for area in serving_areas[:5]:
            coords = area.get("coordinates") or {}
            latitude = coords.get("latitude")
            longitude = coords.get("longitude")
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


class ConfirmRequest(BaseModel):
    session_id: str
    operator_id: str  # id from suggested_operators


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
    bedrock = get_bedrock_client()
    db = await get_database()
    user_id = str(current_user["_id"])

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
                        yield f"data: {json.dumps({'type': 'status', 'text': '🔍 Searching for operators...'})}\n\n"

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

                        # Query real operators from DB
                        matched = await find_matching_operators(
                            db,
                            locations,
                            states,
                            budget_usd=budget_usd,
                            preferences=preferences,
                        )
                        suggested_operators = matched
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
                                    "match_type": op.get("match_type", "similar"),
                                    "match_reason": op.get("match_reason", ""),
                                    "budget_fit": op.get("budget_fit", False),
                                    "preference_fit_count": op.get("preference_fit_count", 0),
                                    "score": op.get("score", 0),
                                }
                                for op in matched
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
