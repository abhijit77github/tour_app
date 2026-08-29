from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


BillingPlanStatus = Literal["active", "inactive"]
ProviderPlanStatus = Literal["active", "pending_activation", "inactive", "cancelled"]
CreditLedgerType = Literal["grant", "debit", "refund", "adjustment", "expiry", "topup"]
BillingSurface = Literal["search", "planner", "quotes", "admin"]
BillingEventType = Literal["impression", "profile_click", "intent_click", "qualified_lead", "conversion"]
PaymentProvider = Literal["razorpay", "stripe", "payu"]
PlanOrderStatus = Literal["pending_payment", "payment_pending", "payment_received", "fulfillment_pending", "completed", "cancelled", "expired", "failed"]
PlanOrderPaymentStatus = Literal["not_started", "pending", "authorized", "paid", "failed", "cancelled", "refunded"]
PlanOrderFulfillmentStatus = Literal["not_started", "pending", "completed", "failed"]


class BillingPlanBase(BaseModel):
    code: str
    name: str
    description: str
    monthly_price: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    included_credits: int = Field(default=0, ge=0)
    is_active: bool = True
    features: list[str] = []

    @field_validator("code", "name", "description", mode="before")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("field is required")
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("currency is required")
        return value.strip().upper()


class BillingPlanCreate(BillingPlanBase):
    pass


class BillingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    included_credits: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    features: Optional[list[str]] = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_optional_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("currency is required")
        return value.strip().upper()


class OperatorPlanSubscribeRequest(BaseModel):
    plan_code: str

    @field_validator("plan_code", mode="before")
    @classmethod
    def clean_plan_code(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("plan_code is required")
        return value.strip().upper()


class OperatorPlanOrderCreateRequest(BaseModel):
    plan_code: str
    payment_provider: PaymentProvider = "razorpay"
    client_request_id: Optional[str] = Field(default=None, max_length=120)

    @field_validator("plan_code", mode="before")
    @classmethod
    def clean_plan_code(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("plan_code is required")
        return value.strip().upper()

    @field_validator("client_request_id", mode="before")
    @classmethod
    def clean_optional_client_request_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PlanOrderPaymentStateUpdateRequest(BaseModel):
    gateway_session_id: Optional[str] = Field(default=None, max_length=160)
    gateway_order_id: Optional[str] = Field(default=None, max_length=160)
    payment_reference: Optional[str] = Field(default=None, max_length=160)
    gateway_metadata: dict = Field(default_factory=dict)

    @field_validator("gateway_session_id", "gateway_order_id", "payment_reference", mode="before")
    @classmethod
    def clean_optional_gateway_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PlanOrderSettlementRequest(BaseModel):
    payment_reference: Optional[str] = Field(default=None, max_length=160)
    gateway_payment_id: Optional[str] = Field(default=None, max_length=160)
    gateway_order_id: Optional[str] = Field(default=None, max_length=160)
    settlement_notes: Optional[str] = Field(default=None, max_length=500)
    gateway_metadata: dict = Field(default_factory=dict)

    @field_validator("payment_reference", "gateway_payment_id", "gateway_order_id", "settlement_notes", mode="before")
    @classmethod
    def clean_optional_settlement_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BillingPlanSnapshot(BaseModel):
    code: str
    name: str
    description: str
    monthly_price: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    included_credits: int = Field(default=0, ge=0)
    features: list[str] = []


class ProviderPlanOrderInDB(BaseModel):
    operator_profile_id: str
    operator_user_id: str
    organization_id: str
    order_code: str
    plan_code: str
    plan_snapshot: BillingPlanSnapshot
    amount: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    payment_provider: PaymentProvider
    order_status: PlanOrderStatus = "pending_payment"
    payment_status: PlanOrderPaymentStatus = "not_started"
    fulfillment_status: PlanOrderFulfillmentStatus = "not_started"
    client_request_id: Optional[str] = None
    payment_reference: Optional[str] = None
    gateway_session_id: Optional[str] = None
    gateway_order_id: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    gateway_metadata: dict = Field(default_factory=dict)
    subscription_snapshot: dict = Field(default_factory=dict)
    status_history: list[dict] = Field(default_factory=list)
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    settled_at: Optional[datetime] = None
    settled_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class ProviderPlanAssignRequest(BaseModel):
    plan_code: str
    notes: Optional[str] = None
    reset_credits: bool = True

    @field_validator("plan_code", mode="before")
    @classmethod
    def clean_plan_code(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("plan_code is required")
        return value.strip().upper()

    @field_validator("notes", mode="before")
    @classmethod
    def clean_optional_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CreditAdjustmentRequest(BaseModel):
    operator_profile_id: str
    credits_delta: int
    notes: str

    @field_validator("operator_profile_id", "notes", mode="before")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("field is required")
        return value.strip()


class RefundCreditCompensationRequest(BaseModel):
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def clean_optional_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PlannerPricingSettingsUpdate(BaseModel):
    search_profile_click: int = Field(default=1, ge=0, le=100)
    planner_intent_click: int = Field(default=0, ge=0, le=100)
    qualified_lead: int = Field(default=0, ge=0, le=100)
    conversion: int = Field(default=0, ge=0, le=100)


class ProviderPlanInDB(BaseModel):
    operator_profile_id: str
    operator_user_id: str
    plan_code: str
    plan_name: str
    plan_status: ProviderPlanStatus = "active"
    included_credits: int = Field(default=0, ge=0)
    credits_remaining: int = Field(default=0, ge=0)
    billing_cycle_start_at: datetime
    billing_cycle_end_at: datetime
    auto_renew: bool = False
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    last_assignment_notes: Optional[str] = None
    last_assigned_by: Optional[str] = None
    last_fulfilled_order_id: Optional[str] = None


class CreditLedgerEntry(BaseModel):
    operator_profile_id: str
    entry_type: CreditLedgerType
    credits_delta: int
    balance_after: int = Field(ge=0)
    source_surface: Optional[BillingSurface] = None
    source_reference_type: str
    source_reference_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None


class BillingEventLog(BaseModel):
    idempotency_key: str
    operator_profile_id: str
    promotion_id: Optional[str] = None
    source_surface: BillingSurface
    event_type: BillingEventType
    source_reference_type: Optional[str] = None
    source_reference_id: Optional[str] = None
    anonymous_session_id: Optional[str] = None
    request_fingerprint: Optional[str] = None
    credits_charged: int = Field(default=0, ge=0)
    currency_amount: float = Field(default=0, ge=0)
    is_billable: bool = False
    outcome_reason: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


DEFAULT_BILLING_PLANS: list[dict] = [
    {
        "code": "FREE",
        "name": "Free",
        "description": "Organic listing with no paid distribution credits.",
        "monthly_price": 0,
        "currency": "INR",
        "included_credits": 0,
        "is_active": True,
        "features": [
            "Organic listing",
            "Standard profile",
            "Standard quote participation",
            "Basic analytics",
        ],
    },
    {
        "code": "GROWTH",
        "name": "Growth",
        "description": "Unlock promoted search with a starter monthly credit allowance.",
        "monthly_price": 2499,
        "currency": "INR",
        "included_credits": 250,
        "is_active": True,
        "features": [
            "Promoted search eligibility",
            "Monthly included credits",
            "Campaign analytics",
        ],
    },
    {
        "code": "PRO",
        "name": "Pro",
        "description": "Higher credit allowance and more headroom for promoted distribution.",
        "monthly_price": 5999,
        "currency": "INR",
        "included_credits": 800,
        "is_active": True,
        "features": [
            "Higher monthly credit allowance",
            "Priority support for campaign operations",
            "Expanded reporting",
        ],
    },
]