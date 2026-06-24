from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketStatus = Literal["open", "acknowledged", "in_progress", "completed"]


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=4, max_length=140)
    description: str = Field(..., min_length=10, max_length=4000)
    category: str = Field(default="general", min_length=2, max_length=50)
    priority: TicketPriority = "medium"
    attachments: list[str] = Field(default_factory=list)


class TicketCommentCreate(BaseModel):
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    attachments: list[str] = Field(default_factory=list)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    public_reply: Optional[str] = Field(default=None, max_length=2000)
    assignee_admin_id: Optional[str] = None