"""Pydantic request/response models for the multi-tenancy endpoints."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class TenantOut(BaseModel):
    """A tenant as returned by the admin listing."""

    id: str
    slug: str
    name: str
    status: str = "active"
    member_count: int = 0


class TenantMemberOut(BaseModel):
    """A user's membership within a tenant (admin view)."""

    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    role: str = "member"
    is_default: bool = False


class MyTenantOut(BaseModel):
    """A tenant the current user belongs to (self view / switcher)."""

    id: str
    slug: str
    name: str
    status: str = "active"
    role: str = "member"
    is_default: bool = False


class CreateTenantRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = Field(default="member")


class TenantStatusRequest(BaseModel):
    status: str = Field(description="active | suspended")


class SwitchTenantRequest(BaseModel):
    tenant_id: str


class TenantPurgeResult(BaseModel):
    """Outcome of a GDPR data purge: rows deleted per table + the total."""

    deleted: Dict[str, int] = Field(default_factory=dict)
    total: int = 0
