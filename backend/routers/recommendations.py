from fastapi import APIRouter, Depends
from datetime import datetime
from typing import List, Dict, Any
from ..database import get_database
from ..routers.auth import get_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _pick_thumbnail(area: dict) -> str:
    images = area.get("images") or []
    if images:
        return images[0]

    for sub in area.get("sub_locations", []):
        sub_images = sub.get("images") or []
        if sub_images:
            return sub_images[0]

    return None


@router.get("/custom")
async def get_custom_recommendations(current_user: dict = Depends(get_current_user)):
    db = await get_database()

    area_entries: List[Dict[str, Any]] = []
    cursor = db.operator_profiles.find({})
    async for op in cursor:
        op_id = str(op["_id"])
        for area in op.get("serving_areas", []):
            entry = {
                "operator_id": op_id,
                "operator_name": op.get("business_name"),
                "area_name": area.get("area_name"),
                "state": area.get("state"),
                "country": area.get("country"),
                "average_rating": float(op.get("average_rating", 0)),
                "total_reviews": int(op.get("total_reviews", 0)),
                "specializations": op.get("specializations", []),
                "thumbnail": _pick_thumbnail(area),
                "sponsored": False,
            }
            area_entries.append(entry)

    def sort_popular(item: Dict[str, Any]):
        return (
            -item.get("average_rating", 0),
            -item.get("total_reviews", 0)
        )

    personalized: List[Dict[str, Any]] = []
    if current_user.get("user_type") == "tourist":
        recent = await db.bookings.find(
            {"tourist_id": str(current_user["_id"])}
        ).sort("created_at", -1).to_list(length=5)

        focus_states = {
            b.get("cart", {}).get("state")
            for b in recent
            if b.get("cart", {}).get("state")
        }
        focus_areas = {
            b.get("cart", {}).get("area_name")
            for b in recent
            if b.get("cart", {}).get("area_name")
        }

        personalized = [
            entry for entry in area_entries
            if entry.get("state") in focus_states
            or entry.get("area_name") in focus_areas
        ]

        if not personalized:
            personalized = sorted(area_entries, key=sort_popular)[:10]
        else:
            personalized = sorted(personalized, key=sort_popular)[:10]
    else:
        personalized = sorted(area_entries, key=sort_popular)[:10]

    popular = sorted(area_entries, key=sort_popular)[:15]

    sponsored_base = sorted(
        area_entries,
        key=lambda item: (
            -item.get("total_reviews", 0),
            -item.get("average_rating", 0)
        )
    )[:4]
    sponsored = [{**item, "sponsored": True} for item in sponsored_base]

    return {
        "user_id": str(current_user["_id"]),
        "personalized": personalized,
        "popular": popular,
        "sponsored": sponsored,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "personalized": len(personalized),
            "popular": len(popular),
            "sponsored": len(sponsored)
        }
    }
