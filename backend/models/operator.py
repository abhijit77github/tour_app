from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId


class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


class SubLocation(BaseModel):
    name: str
    description: Optional[str] = None
    coordinates: Optional[LocationCoordinates] = None
    images: List[str] = []
    estimated_duration: Optional[str] = None  # e.g., "2 hours"
    popular: bool = False


class ServingArea(BaseModel):
    area_name: str
    state: str
    country: str
    description: Optional[str] = None
    sub_locations: List[SubLocation] = []
    images: List[str] = []
    coordinates: Optional[LocationCoordinates] = None


class CarServiceOption(BaseModel):
    vehicle_type: str  # e.g., Sedan, SUV, Hatchback, Tempo Traveler
    vehicle_label: Optional[str] = None
    seats: int
    luggage_capacity: Optional[int] = None
    pricing_model: str = "per_day"  # per_km, per_day, fixed_transfer
    base_fare: Optional[float] = None
    fare_per_km: Optional[float] = None
    operating_hours: Optional[str] = None
    amenities: List[str] = []
    coverage_areas: List[str] = []


class OperatorProfile(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str  # Reference to User
    business_name: str
    description: Optional[str] = None
    serving_areas: List[ServingArea] = []
    profile_image: Optional[str] = None
    contact_number: str
    alternate_contact: Optional[str] = None
    years_of_experience: Optional[int] = None
    specializations: List[str] = []  # e.g., ["Adventure", "Family Tours", "Budget Travel"]
    service_types: List[str] = ["tour"]  # tour, car
    car_services: List[CarServiceOption] = []
    average_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class OperatorProfileCreate(BaseModel):
    business_name: str
    description: Optional[str] = None
    contact_number: str
    alternate_contact: Optional[str] = None
    years_of_experience: Optional[int] = None
    specializations: List[str] = []
    service_types: List[str] = ["tour"]
    car_services: List[CarServiceOption] = []


class OperatorProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    description: Optional[str] = None
    contact_number: Optional[str] = None
    alternate_contact: Optional[str] = None
    years_of_experience: Optional[int] = None
    specializations: Optional[List[str]] = None
    service_types: Optional[List[str]] = None
    car_services: Optional[List[CarServiceOption]] = None
