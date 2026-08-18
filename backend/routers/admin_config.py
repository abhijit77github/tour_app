from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_database
from ..models.system_config import SystemConfigUpdate, QuoteLimitsConfig
from ..routers.admin import get_current_admin

router = APIRouter(prefix="/admin/config", tags=["Admin Configuration"])


@router.get("/quote-limits")
async def get_quote_limits_config(current_admin: dict = Depends(get_current_admin)):
    """
    Get current quote limits configuration.
    
    Returns the configured limits for each membership tier.
    """
    db = await get_database()
    
    config = await db.system_config.find_one({"config_key": "quote_limits"})
    
    if not config:
        # Return default values if config doesn't exist
        return {
            "config_key": "quote_limits",
            "quote_limits": {
                "free": 5,
                "premium": 20,
                "enterprise": 100
            },
            "updated_at": None,
            "updated_by": None,
            "updated": None
        }
    
    # Format response
    response = {
        "config_key": config.get("config_key"),
        "quote_limits": config.get("quote_limits", {}),
        "updated_at": config.get("updated_at"),
        "updated_by": config.get("updated_by")
    }
    
    # Add updated metadata for UI display
    if config.get("updated_at") and config.get("updated_by"):
        admin = await db.admins.find_one({"_id": config["updated_by"]})
        admin_email = admin.get("email", "Unknown") if admin else "Unknown"
        response["updated"] = {
            "date": config["updated_at"],
            "admin": admin_email
        }
    else:
        response["updated"] = None
    
    return response


@router.put("/quote-limits")
async def update_quote_limits_config(
    config_update: SystemConfigUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Update quote limits configuration.
    
    Allows admins to configure the maximum number of open quotes per membership tier.
    Changes take effect immediately for all new quote requests.
    """
    db = await get_database()
    
    # Validate limits are within acceptable ranges
    limits = config_update.quote_limits
    
    if limits.free < 1 or limits.free > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free tier limit must be between 1 and 50"
        )
    
    if limits.premium < 1 or limits.premium > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Premium tier limit must be between 1 and 100"
        )
    
    if limits.enterprise < 1 or limits.enterprise > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enterprise tier limit must be between 1 and 500"
        )
    
    # Ensure limits are in ascending order (optional business rule)
    if not (limits.free <= limits.premium <= limits.enterprise):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limits should be in ascending order: free <= premium <= enterprise"
        )
    
    # Update or insert config
    update_doc = {
        "config_key": "quote_limits",
        "quote_limits": {
            "free": limits.free,
            "premium": limits.premium,
            "enterprise": limits.enterprise
        },
        "updated_at": datetime.now(timezone.utc),
        "updated_by": str(current_admin["_id"])
    }
    
    result = await db.system_config.update_one(
        {"config_key": "quote_limits"},
        {"$set": update_doc},
        upsert=True
    )
    
    # Fetch updated config
    updated_config = await db.system_config.find_one({"config_key": "quote_limits"})
    
    # Get admin info for response
    admin_email = current_admin.get("email", "Unknown")
    
    return {
        "message": "Quote limits updated successfully",
        "config": {
            "config_key": updated_config.get("config_key"),
            "quote_limits": updated_config.get("quote_limits"),
            "updated_at": updated_config.get("updated_at"),
            "updated_by": updated_config.get("updated_by"),
            "updated": {
                "date": updated_config.get("updated_at"),
                "admin": admin_email
            }
        }
    }
