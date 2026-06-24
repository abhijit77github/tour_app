from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .promotion import PromotionLocationScope, PromotionServiceType


PaymentProvider = Literal["razorpay", "stripe", "payu"]
PromotionOrderStatus = Literal["pending_payment", "payment_pending", "paid", "cancelled", "expired"]
PaymentStatus = Literal["not_started", "pending", "paid", "failed", "cancelled"]


class PromotionPackage(BaseModel):
    code: str
    name: str
    description: str
    duration_days: int = Field(ge=1)
    available_service_types: list[PromotionServiceType]
    priority: int = Field(default=50, ge=0, le=100)
    promotion_label: str = Field(default="Promoted", max_length=40)
    price: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    requires_admin_approval: bool = True
    is_active: bool = True
    features: list[str] = []

    @field_validator("code", "name", "description", "promotion_label", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Field is required")
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("currency is required")
        return value.strip().upper()


class PromotionPackageInDB(PromotionPackage):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class PromotionPurchaseRequest(BaseModel):
    package_id: str
    location_scope: PromotionLocationScope
    service_type: PromotionServiceType
    payment_provider: PaymentProvider

    @field_validator("package_id", mode="before")
    @classmethod
    def validate_package_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("package_id is required")
        return value.strip()


class PromotionOrderPackageSnapshot(BaseModel):
    code: str
    name: str
    duration_days: int
    priority: int
    promotion_label: str
    price: float
    currency: str
    requires_admin_approval: bool
    features: list[str] = []


class PromotionOrder(BaseModel):
    operator_profile_id: str
    operator_user_id: str
    package_id: str
    package_snapshot: PromotionOrderPackageSnapshot
    location_scope: PromotionLocationScope
    normalized_location_scope: PromotionLocationScope
    service_type: PromotionServiceType
    payment_provider: PaymentProvider
    amount: float
    currency: str = "INR"
    order_status: PromotionOrderStatus = "pending_payment"
    payment_status: PaymentStatus = "not_started"
    payment_reference: Optional[str] = None
    gateway_session_id: Optional[str] = None
    campaign_status: str = "awaiting_payment"
    created_at: datetime
    updated_at: datetime


DEFAULT_PROMOTION_PACKAGES: list[dict] = [
    {
        "code": "STARTER_7D_SINGLE_LOCATION",
        "name": "Starter Boost",
        "description": "Get highlighted in one destination search for 7 days.",
        "duration_days": 7,
        "available_service_types": ["tour", "car"],
        "priority": 55,
        "promotion_label": "Promoted",
        "price": 1499,
        "currency": "INR",
        "requires_admin_approval": True,
        "is_active": True,
        "features": [
            "One location targeting",
            "Tour or car service support",
            "Priority placement above organic results"
        ]
    },
    {
        "code": "BOOST_14D_SINGLE_LOCATION",
        "name": "Boost 14 Days",
        "description": "Stay promoted for two weeks in a single destination.",
        "duration_days": 14,
        "available_service_types": ["tour", "car"],
        "priority": 65,
        "promotion_label": "Promoted",
        "price": 2999,
        "currency": "INR",
        "requires_admin_approval": True,
        "is_active": True,
        "features": [
            "Two-week visibility",
            "Higher ranking priority",
            "Performance tracking ready"
        ]
    },
    {
        "code": "PREMIUM_30D_LOCATION",
        "name": "Premium Month",
        "description": "Longer visibility with the highest starter priority for one location.",
        "duration_days": 30,
        "available_service_types": ["tour", "car"],
        "priority": 80,
        "promotion_label": "Promoted",
        "price": 5499,
        "currency": "INR",
        "requires_admin_approval": True,
        "is_active": True,
        "features": [
            "30-day promotion window",
            "Highest package priority",
            "Ready for future Razorpay / Stripe / PayU checkout"
        ]
    }
]