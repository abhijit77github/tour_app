from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


PrincipalType = Literal["user", "admin"]
OrganizationType = Literal["operator", "internal_admin"]
MembershipStatus = Literal["invited", "active", "suspended", "revoked"]


class Organization(BaseModel):
    name: str
    slug: str
    organization_type: OrganizationType
    status: str = "active"
    operator_profile_id: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class OrganizationMembership(BaseModel):
    organization_id: str
    principal_type: PrincipalType
    principal_id: str
    membership_status: MembershipStatus = "active"
    role_keys: list[str] = Field(default_factory=list)
    permission_overrides: dict[str, list[str]] = Field(default_factory=dict)
    scope_constraints: dict[str, Any] = Field(default_factory=dict)
    invited_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_accepted_at: Optional[datetime] = None


class OrganizationMemberUpsert(BaseModel):
    email: str
    full_name: str
    phone: Optional[str] = None
    role_keys: list[str] = Field(default_factory=list)
    password: Optional[str] = None
    permission_overrides: dict[str, list[str]] = Field(default_factory=dict)
    scope_constraints: dict[str, Any] = Field(default_factory=dict)


class OrganizationMembershipUpdate(BaseModel):
    role_keys: Optional[list[str]] = None
    membership_status: Optional[MembershipStatus] = None
    permission_overrides: Optional[dict[str, list[str]]] = None
    scope_constraints: Optional[dict[str, Any]] = None
