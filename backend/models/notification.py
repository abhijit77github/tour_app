from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


NotificationType = Literal["notification", "announcement", "alert"]
NotificationStatus = Literal["draft", "scheduled", "processing", "sent", "failed", "cancelled"]
RecipientType = Literal["tourists", "operators", "all"]
NotificationChannel = Literal["in_app", "email", "sms"]
AdminAlertSeverity = Literal["info", "warning", "error"]


class RecipientFilter(BaseModel):
    active_only: bool = False
    last_active_days: Optional[int] = Field(default=None, ge=1, le=365)


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: bool = True
    marketing_enabled: bool = True
    announcements_enabled: bool = True
    alerts_enabled: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str = "UTC"

    @field_validator("quiet_hours_start", "quiet_hours_end", mode="before")
    @classmethod
    def clean_optional_clock_value(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        parts = cleaned.split(":")
        if len(parts) != 2:
            raise ValueError("time must be in HH:MM format")
        hour, minute = parts
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError("time must be in HH:MM format")
        hour_num = int(hour)
        minute_num = int(minute)
        if hour_num < 0 or hour_num > 23 or minute_num < 0 or minute_num > 59:
            raise ValueError("time must be in HH:MM format")
        return f"{hour_num:02d}:{minute_num:02d}"

    @field_validator("timezone", mode="before")
    @classmethod
    def clean_timezone(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("timezone is required")
        return value.strip()

    @model_validator(mode="after")
    def validate_quiet_hours(self):
        if self.quiet_hours_enabled and (not self.quiet_hours_start or not self.quiet_hours_end):
            raise ValueError("quiet hours start and end are required when quiet hours are enabled")
        return self


class NotificationAudiencePreviewRequest(BaseModel):
    recipient_type: RecipientType
    recipient_filter: RecipientFilter = Field(default_factory=RecipientFilter)


class NotificationTemplateCreate(BaseModel):
    name: str
    category: str
    subject: str
    message: str
    channels: list[NotificationChannel] = Field(default_factory=lambda: ["in_app"])
    is_active: bool = True

    @field_validator("name", "category", "subject", "message", mode="before")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("field is required")
        return value.strip()

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, value: str) -> str:
        if len(value) > 1000:
            raise ValueError("message cannot exceed 1000 characters")
        return value


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    channels: Optional[list[NotificationChannel]] = None
    is_active: Optional[bool] = None

    @field_validator("name", "category", "subject", "message", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("field is required")
        cleaned = value.strip()
        if cleaned and len(cleaned) > 1000 and cls.__name__ == "NotificationTemplateUpdate":
            if cleaned == value and len(cleaned) > 1000:
                raise ValueError("message cannot exceed 1000 characters")
        return cleaned

    @field_validator("message")
    @classmethod
    def validate_optional_message_length(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 1000:
            raise ValueError("message cannot exceed 1000 characters")
        return value


class NotificationCampaignCreate(BaseModel):
    type: NotificationType = "notification"
    subject: str
    message: str
    channel: NotificationChannel = "in_app"
    recipient_type: RecipientType
    recipient_filter: RecipientFilter = Field(default_factory=RecipientFilter)
    send_now: bool = True
    scheduled_for: Optional[datetime] = None
    template_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("subject", "message", mode="before")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("field is required")
        return value.strip()

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, value: str) -> str:
        if len(value) > 1000:
            raise ValueError("message cannot exceed 1000 characters")
        return value

    @field_validator("template_id", mode="before")
    @classmethod
    def clean_optional_template_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.send_now and self.scheduled_for is not None:
            raise ValueError("scheduled_for must be empty when send_now is true")
        if not self.send_now and self.scheduled_for is None:
            raise ValueError("scheduled_for is required when send_now is false")
        return self