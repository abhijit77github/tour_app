from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator

from .operator import LocationCoordinates
from .user import PyObjectId


BudgetBand = Literal["budget", "mid", "premium"]
TemplateStatus = Literal["draft", "published", "archived"]
TouristItineraryStatus = Literal["draft", "saved", "shared"]
SourceType = Literal["manual", "template_based", "llm_adapted", "operator_proposed"]


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class ItineraryLocation(BaseModel):
    area_name: str
    state: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[LocationCoordinates] = None

    @field_validator("area_name", mode="before")
    @classmethod
    def clean_area_name(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("area_name is required")
        return cleaned

    @field_validator("state", "country", mode="before")
    @classmethod
    def clean_optional_fields(cls, value: Optional[str]) -> Optional[str]:
        return _clean_text(value)


class ItineraryDayItem(BaseModel):
    day_number: int = Field(ge=1)
    title: str
    summary: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)
    overnight_location: Optional[str] = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("title is required")
        return cleaned

    @field_validator("summary", "overnight_location", mode="before")
    @classmethod
    def clean_optionals(cls, value: Optional[str]) -> Optional[str]:
        return _clean_text(value)

    @field_validator("highlights", mode="before")
    @classmethod
    def clean_highlights(cls, value):
        if not value:
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class OperatorItineraryTemplateBase(BaseModel):
    title: str
    summary: Optional[str] = None
    primary_location: ItineraryLocation
    route_locations: list[ItineraryLocation] = Field(default_factory=list)
    duration_days: int = Field(ge=1, le=30)
    trip_styles: list[str] = Field(default_factory=list)
    traveler_types: list[str] = Field(default_factory=list)
    season_tags: list[str] = Field(default_factory=list)
    budget_band: Optional[BudgetBand] = None
    notes_for_planner: Optional[str] = None
    days: list[ItineraryDayItem] = Field(default_factory=list)
    status: TemplateStatus = "draft"

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("title is required")
        return cleaned

    @field_validator("summary", "notes_for_planner", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return _clean_text(value)

    @field_validator("trip_styles", "traveler_types", "season_tags", mode="before")
    @classmethod
    def clean_tags(cls, value):
        if not value:
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @model_validator(mode="after")
    def validate_days(self):
        if self.days and len(self.days) > self.duration_days:
            raise ValueError("days cannot exceed duration_days")
        return self


class OperatorItineraryTemplateCreate(OperatorItineraryTemplateBase):
    pass


class OperatorItineraryTemplateUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    primary_location: Optional[ItineraryLocation] = None
    route_locations: Optional[list[ItineraryLocation]] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=30)
    trip_styles: Optional[list[str]] = None
    traveler_types: Optional[list[str]] = None
    season_tags: Optional[list[str]] = None
    budget_band: Optional[BudgetBand] = None
    notes_for_planner: Optional[str] = None
    days: Optional[list[ItineraryDayItem]] = None
    status: Optional[TemplateStatus] = None


class TouristItineraryBase(BaseModel):
    title: str
    summary: Optional[str] = None
    primary_location: Optional[ItineraryLocation] = None
    route_locations: list[ItineraryLocation] = Field(default_factory=list)
    duration_days: int = Field(ge=1, le=30)
    trip_styles: list[str] = Field(default_factory=list)
    travelers: Optional[int] = Field(default=None, ge=1)
    budget_band: Optional[BudgetBand] = None
    notes: Optional[str] = None
    days: list[ItineraryDayItem] = Field(default_factory=list)
    status: TouristItineraryStatus = "saved"
    source_type: SourceType = "manual"
    source_template_ids: list[str] = Field(default_factory=list)
    shareable_to_quote: bool = True

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("title is required")
        return cleaned

    @field_validator("summary", "notes", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return _clean_text(value)

    @field_validator("trip_styles", "source_template_ids", mode="before")
    @classmethod
    def clean_lists(cls, value):
        if not value:
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @model_validator(mode="after")
    def validate_days(self):
        if self.days and len(self.days) > self.duration_days:
            raise ValueError("days cannot exceed duration_days")
        return self


class TouristItineraryCreate(TouristItineraryBase):
    pass


class TouristItineraryUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    primary_location: Optional[ItineraryLocation] = None
    route_locations: Optional[list[ItineraryLocation]] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=30)
    trip_styles: Optional[list[str]] = None
    travelers: Optional[int] = Field(default=None, ge=1)
    budget_band: Optional[BudgetBand] = None
    notes: Optional[str] = None
    days: Optional[list[ItineraryDayItem]] = None
    status: Optional[TouristItineraryStatus] = None
    source_type: Optional[SourceType] = None
    source_template_ids: Optional[list[str]] = None
    shareable_to_quote: Optional[bool] = None


class ItinerarySearchQuery(BaseModel):
    area_name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=30)
    trip_styles: list[str] = Field(default_factory=list)
    traveler_types: list[str] = Field(default_factory=list)
    budget_band: Optional[BudgetBand] = None


class OperatorItineraryTemplate(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    operator_profile_id: str
    operator_user_id: str
    operator_name: Optional[str] = None
    title: str
    summary: Optional[str] = None
    primary_location: ItineraryLocation
    route_locations: list[ItineraryLocation] = Field(default_factory=list)
    duration_days: int
    trip_styles: list[str] = Field(default_factory=list)
    traveler_types: list[str] = Field(default_factory=list)
    season_tags: list[str] = Field(default_factory=list)
    budget_band: Optional[BudgetBand] = None
    notes_for_planner: Optional[str] = None
    days: list[ItineraryDayItem] = Field(default_factory=list)
    status: TemplateStatus = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TouristItinerary(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tourist_id: str
    title: str
    summary: Optional[str] = None
    primary_location: Optional[ItineraryLocation] = None
    route_locations: list[ItineraryLocation] = Field(default_factory=list)
    duration_days: int
    trip_styles: list[str] = Field(default_factory=list)
    travelers: Optional[int] = None
    budget_band: Optional[BudgetBand] = None
    notes: Optional[str] = None
    days: list[ItineraryDayItem] = Field(default_factory=list)
    status: TouristItineraryStatus = "saved"
    source_type: SourceType = "manual"
    source_template_ids: list[str] = Field(default_factory=list)
    shareable_to_quote: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}