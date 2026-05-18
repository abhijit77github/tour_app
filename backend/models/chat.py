from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from .user import PyObjectId


class ChatMessage(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    sender_id: str
    receiver_id: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ChatMessageCreate(BaseModel):
    receiver_id: str
    message: str


class ChatConversation(BaseModel):
    """Represents a conversation between two users"""
    user_id: str
    other_user_id: str
    other_user_name: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0


class ChatMessageResponse(BaseModel):
    id: str = Field(alias="_id")
    sender_id: str
    receiver_id: str
    message: str
    timestamp: datetime
    read: bool
    
    class Config:
        populate_by_name = True
