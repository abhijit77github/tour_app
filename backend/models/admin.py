from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from bson import ObjectId
from email_validator import EmailNotValidError, validate_email


def validate_app_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email:
        raise ValueError("Email must contain @")
    local_part, domain = email.rsplit("@", 1)
    if not local_part or not domain:
        raise ValueError("Invalid email address")
    if domain.endswith(".local"):
        return email
    try:
        return validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


class AdminBase(BaseModel):
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str = Field(default="moderator", description="super_admin or moderator")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


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
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class AdminToken(BaseModel):
    access_token: str
    token_type: str
    admin: Admin
