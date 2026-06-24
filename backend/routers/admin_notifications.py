from fastapi import APIRouter, Depends, status

from ..database import get_database
from ..models.notification import (
    NotificationAudiencePreviewRequest,
    NotificationCampaignCreate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)
from ..routers.admin import get_current_admin
from ..utils.notification_delivery import run_notification_worker_once
from ..utils.notifications import (
    create_notification_campaign,
    create_notification_template,
    delete_notification_template,
    get_notification_campaign,
    get_notification_summary,
    list_admin_alerts,
    list_delivery_attempts,
    list_notification_campaigns,
    list_notification_templates,
    list_worker_runs,
    mark_admin_alert_as_read,
    mark_all_admin_alerts_as_read,
    preview_notification_audience,
    update_notification_template,
)


router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])


@router.get("/summary")
async def get_admin_notification_summary(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    return await get_notification_summary(db)


@router.get("/alerts")
async def get_admin_notification_alerts(
    unread_only: bool = False,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    return {"alerts": await list_admin_alerts(db, unread_only=unread_only)}


@router.post("/alerts/{alert_id}/read")
async def read_admin_notification_alert(
    alert_id: str,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    alert = await mark_admin_alert_as_read(db, alert_id)
    return {"message": "Alert marked as read", "alert": alert}


@router.post("/alerts/read-all")
async def read_all_admin_notification_alerts(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    result = await mark_all_admin_alerts_as_read(db)
    return {"message": "Alerts marked as read", **result}


@router.post("/audience-preview")
async def preview_admin_notification_audience(
    payload: NotificationAudiencePreviewRequest,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    return await preview_notification_audience(
        db,
        recipient_type=payload.recipient_type,
        recipient_filter=payload.recipient_filter.model_dump(),
    )


@router.get("/templates")
async def get_notification_templates(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    return {"templates": await list_notification_templates(db)}


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_admin_notification_template(
    payload: NotificationTemplateCreate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    template = await create_notification_template(db, payload.model_dump(), admin=admin)
    return {"message": "Template created", "template": template}


@router.put("/templates/{template_id}")
async def update_admin_notification_template(
    template_id: str,
    payload: NotificationTemplateUpdate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    template = await update_notification_template(
        db,
        template_id,
        payload.model_dump(exclude_none=True),
        admin=admin,
    )
    return {"message": "Template updated", "template": template}


@router.delete("/templates/{template_id}")
async def delete_admin_notification_template(
    template_id: str,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    await delete_notification_template(db, template_id, admin=admin)
    return {"message": "Template deleted"}


@router.get("/campaigns")
async def get_admin_notification_campaigns(
    type: str | None = None,
    status_value: str | None = None,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    campaigns = await list_notification_campaigns(db, campaign_type=type, status_value=status_value)
    return {"campaigns": campaigns}


@router.get("/campaigns/{campaign_id}")
async def get_admin_notification_campaign(
    campaign_id: str,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    campaign = await get_notification_campaign(db, campaign_id)
    return {"campaign": campaign}


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_admin_notification_campaign(
    payload: NotificationCampaignCreate,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    campaign = await create_notification_campaign(db, payload.model_dump(), admin=admin)
    return {"message": "Campaign stored", "campaign": campaign}


@router.get("/deliveries")
async def get_admin_notification_deliveries(
    campaign_id: str | None = None,
    admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    return {"attempts": await list_delivery_attempts(db, campaign_id=campaign_id, limit=150)}


@router.get("/worker-runs")
async def get_admin_notification_worker_runs(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    return {"runs": await list_worker_runs(db)}


@router.post("/worker-runs/trigger")
async def trigger_admin_notification_worker(admin: dict = Depends(get_current_admin)):
    db = await get_database()
    result = await run_notification_worker_once(db, worker_id=f"manual:{admin.get('_id')}")
    return {"message": "Notification worker run completed", "result": result}