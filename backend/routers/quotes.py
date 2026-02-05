from datetime import datetime

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
    payload["created_at"] = datetime.utcnow()
    payload["updated_at"] = datetime.utcnow()

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
        "created_at": datetime.utcnow()
    }

    await db.quote_requests.update_one(
        {"_id": ObjectId(quote_id)},
        {
            "$push": {"responses": response_entry},
            "$set": {"status": "responded", "updated_at": datetime.utcnow()}
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
        {"$set": {"status": "closed", "updated_at": datetime.utcnow()}}
    )

    return {"message": "Quote closed"}
