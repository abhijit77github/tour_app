from fastapi import APIRouter, Depends, Query

from ..database import get_database
from ..models.notification import NotificationPreferenceUpdate
from ..routers.auth import get_current_user
from ..utils.notifications import (
    get_notification_preferences,
    get_user_notification_summary,
    list_notification_deliveries,
    list_notification_deliveries_page,
    mark_all_user_notifications_as_read,
    mark_notification_delivery_as_read,
    update_notification_preferences,
)


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/summary")
async def get_notification_summary_for_user(current_user: dict = Depends(get_current_user)):
    db = await get_database()
    return await get_user_notification_summary(db, user_id=str(current_user["_id"]))


@router.get("/inbox")
async def get_notification_inbox(
    unread_only: bool = False,
    cursor: str | None = None,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    deliveries = await list_notification_deliveries_page(
        db,
        user_id=str(current_user["_id"]),
        unread_only=unread_only,
        cursor=cursor,
        page_size=page_size,
    )
    return deliveries


@router.post("/inbox/{delivery_id}/read")
async def mark_notification_inbox_item_read(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    item = await mark_notification_delivery_as_read(
        db,
        delivery_id=delivery_id,
        user_id=str(current_user["_id"]),
    )
    return {"message": "Notification marked as read", "item": item}


@router.post("/inbox/read-all")
async def mark_all_notification_inbox_items_read(current_user: dict = Depends(get_current_user)):
    db = await get_database()
    result = await mark_all_user_notifications_as_read(db, user_id=str(current_user["_id"]))
    return {"message": "Notifications marked as read", **result}


@router.get("/preferences")
async def get_notification_preferences_for_user(current_user: dict = Depends(get_current_user)):
    db = await get_database()
    return await get_notification_preferences(db, user_id=str(current_user["_id"]))


@router.put("/preferences")
async def update_notification_preferences_for_user(
    payload: NotificationPreferenceUpdate,
    current_user: dict = Depends(get_current_user),
):
    db = await get_database()
    updated = await update_notification_preferences(
        db,
        user_id=str(current_user["_id"]),
        payload=payload.model_dump(),
    )
    return {"message": "Notification preferences updated", **updated}