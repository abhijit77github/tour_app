from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


PlannerRewardType = Literal["ad", "promotion"]


class PlannerTouristQuotaSettingsUpdate(BaseModel):
    daily_limit: int = Field(default=3, ge=0, le=100)
    monthly_limit: int = Field(default=10, ge=0, le=1000)
    ad_reward_daily_credits: int = Field(default=1, ge=0, le=20)
    ad_reward_monthly_credits: int = Field(default=1, ge=0, le=100)
    promotion_reward_daily_credits: int = Field(default=1, ge=0, le=20)
    promotion_reward_monthly_credits: int = Field(default=2, ge=0, le=100)


class PlannerRewardGrantRequest(BaseModel):
    reward_id: str
    reward_type: PlannerRewardType

    @field_validator("reward_id", mode="before")
    @classmethod
    def clean_reward_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("reward_id is required")
        return value.strip()


class PlannerQuotaStatus(BaseModel):
    user_id: str
    day_key: str
    month_key: str
    used_today: int = Field(default=0, ge=0)
    used_this_month: int = Field(default=0, ge=0)
    bonus_daily_credits: int = Field(default=0, ge=0)
    bonus_monthly_credits: int = Field(default=0, ge=0)
    daily_limit: int = Field(default=0, ge=0)
    monthly_limit: int = Field(default=0, ge=0)
    effective_daily_limit: int = Field(default=0, ge=0)
    effective_monthly_limit: int = Field(default=0, ge=0)
    daily_remaining: int = Field(default=0, ge=0)
    monthly_remaining: int = Field(default=0, ge=0)
    daily_resets_at: str
    monthly_resets_at: str
    last_request_at: Optional[str] = None
from typing import Literal

from pydantic import BaseModel, Field, field_validator


PlannerRewardType = Literal["ad", "promotion"]


class PlannerQuotaSettingsUpdate(BaseModel):
    daily_limit: int = Field(default=3, ge=0, le=1000)
    monthly_limit: int = Field(default=10, ge=0, le=10000)
    ad_reward_daily_bonus: int = Field(default=1, ge=0, le=100)
    ad_reward_monthly_bonus: int = Field(default=1, ge=0, le=1000)
    promotion_reward_daily_bonus: int = Field(default=1, ge=0, le=100)
    promotion_reward_monthly_bonus: int = Field(default=2, ge=0, le=1000)


class PlannerRewardGrantRequest(BaseModel):
    reward_id: str
    reward_type: PlannerRewardType
    metadata: dict = Field(default_factory=dict)

    @field_validator("reward_id", mode="before")
    @classmethod
    def clean_reward_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("reward_id is required")
        return value.strip()