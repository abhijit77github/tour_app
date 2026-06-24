from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


PromotionStatus = Literal["draft", "pending_approval", "active", "paused", "ended", "rejected"]
PromotionServiceType = Literal["tour", "car"]


def _clean_location_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class PromotionLocationScope(BaseModel):
    area_name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    @field_validator("area_name", "state", "country", mode="before")
    @classmethod
    def clean_values(cls, value: Optional[str]) -> Optional[str]:
        return _clean_location_value(value)

    @model_validator(mode="after")
    def ensure_any_location_field(self):
        if not any([self.area_name, self.state, self.country]):
            raise ValueError("At least one location field is required")
        return self


class LocationPromotionBase(BaseModel):
    operator_profile_id: str
    location_scope: PromotionLocationScope
    start_at: datetime
    end_at: datetime
    service_type: Optional[PromotionServiceType] = None
    status: PromotionStatus = "draft"
    priority: int = Field(default=50, ge=0, le=100)
    promotion_label: str = Field(default="Promoted", max_length=40)
    daily_budget: Optional[float] = Field(default=None, ge=0)
    total_budget: Optional[float] = Field(default=None, ge=0)
    daily_spend: float = Field(default=0, ge=0)
    total_spend: float = Field(default=0, ge=0)
    bid_amount: Optional[float] = Field(default=None, ge=0)
    last_daily_reset_at: Optional[datetime] = None

    @field_validator("operator_profile_id", mode="before")
    @classmethod
    def clean_operator_profile_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("operator_profile_id is required")
        return value.strip()

    @field_validator("promotion_label", mode="before")
    @classmethod
    def clean_label(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("promotion_label is required")
        return value.strip()

    @model_validator(mode="after")
    def validate_date_window(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class LocationPromotionCreate(LocationPromotionBase):
    pass


class LocationPromotionUpdate(BaseModel):
    location_scope: Optional[PromotionLocationScope] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    service_type: Optional[PromotionServiceType] = None
    status: Optional[PromotionStatus] = None
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    promotion_label: Optional[str] = Field(default=None, max_length=40)
    daily_budget: Optional[float] = Field(default=None, ge=0)
    total_budget: Optional[float] = Field(default=None, ge=0)
    daily_spend: Optional[float] = Field(default=None, ge=0)
    total_spend: Optional[float] = Field(default=None, ge=0)
    bid_amount: Optional[float] = Field(default=None, ge=0)

    @field_validator("promotion_label", mode="before")
    @classmethod
    def clean_optional_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocationPromotionInDB(LocationPromotionBase):
    id: str = Field(alias="_id")
    normalized_location_scope: PromotionLocationScope
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    total_impressions: int = 0
    total_clicks: int = 0
    last_served_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class PromotionClickCreate(BaseModel):
    source: str = Field(default="search", max_length=40)
    area_name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    service_type: Optional[PromotionServiceType] = None
    session_id: Optional[str] = Field(default=None, max_length=120)
    request_id: Optional[str] = Field(default=None, max_length=120)

    @field_validator("source", mode="before")
    @classmethod
    def clean_source(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            return "search"
        return value.strip()

    @field_validator("session_id", "request_id", mode="before")
    @classmethod
    def clean_optional_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None