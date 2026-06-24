from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


BackupDestination = Literal["local", "s3"]
BackupJobType = Literal["backup", "restore"]


class BackupJobCreate(BaseModel):
    destination: BackupDestination
    label: Optional[str] = Field(default=None, max_length=80)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        return cleaned or None


class BackupRestoreRequest(BaseModel):
    source: BackupDestination
    confirmation_code: str = Field(min_length=4, max_length=64)
    drop_existing_data: bool = False

    @field_validator("confirmation_code")
    @classmethod
    def normalize_confirmation_code(cls, value: str) -> str:
        return value.strip().upper()


class BackupArtifact(BaseModel):
    file_name: str
    size_bytes: int = 0
    sha256: Optional[str] = None
    local_path: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None


class BackupJob(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    job_code: str
    job_type: BackupJobType
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    destination: Optional[BackupDestination] = None
    source: Optional[BackupDestination] = None
    label: Optional[str] = None
    error_message: Optional[str] = None
    source_backup_id: Optional[str] = None
    artifact: Optional[BackupArtifact] = None
    created_by: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}