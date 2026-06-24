from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from email_validator import EmailNotValidError, validate_email


def validate_app_email(value: str) -> str:
    """Accept normal emails and local-dev domains such as *.local."""
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


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    user_type: str = Field(..., description="operator or tourist")
    

class UserCreate(UserBase):
    password: str


class RegistrationOTPVerifyRequest(BaseModel):
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class ResendActivationOTPRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class UserInDB(UserBase):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class User(UserBase):
    id: str = Field(alias="_id")
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    """Request to initiate forgot password flow"""
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class VerifyOTPRequest(BaseModel):
    """Verify OTP for password reset"""
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)


class ResetPasswordRequest(BaseModel):
    """Reset password with OTP"""
    email: str
    otp: str
    verification_token: str = Field(..., min_length=1, description="Short-lived token issued after OTP verification")
    new_password: str = Field(..., min_length=8, description="Must be at least 8 characters")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_app_email(value)