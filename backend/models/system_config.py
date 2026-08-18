from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuoteLimitsConfig(BaseModel):
    """Configuration for quote request limits per membership tier."""
    free: int = Field(default=5, ge=1, le=50, description="Maximum open quotes for free members")
    premium: int = Field(default=20, ge=1, le=100, description="Maximum open quotes for premium members")
    enterprise: int = Field(default=100, ge=1, le=500, description="Maximum open quotes for enterprise members")


class SystemConfig(BaseModel):
    """System-wide configuration stored in database."""
    config_key: str = Field(..., description="Unique identifier for this config (e.g., 'quote_limits')")
    quote_limits: QuoteLimitsConfig
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(None, description="Admin user ID who last updated this config")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemConfigUpdate(BaseModel):
    """Model for updating system configuration."""
    quote_limits: QuoteLimitsConfig
