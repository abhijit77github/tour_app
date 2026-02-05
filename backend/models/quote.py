from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .operator import LocationCoordinates
from .user import PyObjectId


class QuoteLocation(BaseModel):
    name: str
    state: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[LocationCoordinates] = None
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    operator_id: str
    operator_user_id: str
    operator_name: Optional[str] = None
    amount: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuoteRequest(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tourist_id: str
    tourist_name: Optional[str] = None
    locations: List[QuoteLocation]
    notes: Optional[str] = None
    budget: Optional[float] = None
    travel_window: Optional[str] = None
    travelers: Optional[int] = None
    status: str = "open"
    responses: List[QuoteResponse] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class QuoteRequestCreate(BaseModel):
    locations: List[QuoteLocation]
    notes: Optional[str] = None
    budget: Optional[float] = None
    travel_window: Optional[str] = None
    travelers: Optional[int] = None


class QuoteResponseCreate(BaseModel):
    amount: Optional[float] = None
    message: Optional[str] = None
