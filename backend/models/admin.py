from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class AdminBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = Field(default="moderator", description="super_admin or moderator")


class AdminCreate(AdminBase):
    password: str


class AdminInDB(AdminBase):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Admin(AdminBase):
    id: str = Field(alias="_id")
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminToken(BaseModel):
    access_token: str
    token_type: str
    admin: Admin
