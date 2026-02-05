from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId


class CartItem(BaseModel):
    sub_location_name: str
    description: Optional[str] = None
    selected: bool = True


class TourCart(BaseModel):
    operator_id: Optional[str] = None
    area_name: str
    state: str
    country: Optional[str] = None
    items: List[CartItem] = Field(default_factory=list)


class BookingStatus(BaseModel):
    status: str = "pending"  # pending, confirmed, completed, cancelled
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Booking(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tourist_id: str  # Reference to User
    operator_id: str  # Reference to Operator
    cart: TourCart
    booking_status: BookingStatus = Field(default_factory=BookingStatus)
    estimated_cost: Optional[float] = None
    final_cost: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class BookingCreate(BaseModel):
    operator_id: str
    cart: TourCart
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class Rating(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    booking_id: str
    tourist_id: str
    operator_id: str
    rating: float = Field(..., ge=1, le=5)
    review: Optional[str] = None
    categories: Optional[dict] = None  # e.g., {"hospitality": 5, "value": 4, "experience": 5}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class RatingCreate(BaseModel):
    booking_id: str
    operator_id: str
    rating: float = Field(..., ge=1, le=5)
    review: Optional[str] = None
    categories: Optional[dict] = None
