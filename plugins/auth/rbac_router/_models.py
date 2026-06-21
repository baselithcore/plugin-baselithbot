"""Pydantic request/response models for the RBAC API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    slug: str
    description: str = ""
    category: str = "general"


class RoleOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str = ""
    is_system: bool = False
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_\-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class RolePermissions(BaseModel):
    permissions: List[str] = Field(default_factory=list)


class AssignRole(BaseModel):
    role_id: str


class TabPolicyOut(BaseModel):
    plugin: str
    tab_id: str
    label: str = ""
    restricted: bool = False


class TabRestrict(BaseModel):
    restricted: bool


class AccessibleTab(BaseModel):
    plugin: str
    tab_id: str
    label: str = ""
    restricted: bool = False
    allowed: bool = True
    # True when the owning plugin is platform infrastructure (manifest
    # ``system: true``) — admin-only by default and hidden from user nav.
    system: bool = False


class MePermissions(BaseModel):
    permissions: List[str] = Field(default_factory=list)


class GroupOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str = ""
    is_system: bool = False
    mfa_required: bool = False
    member_count: int = 0
    roles: List[str] = Field(default_factory=list)


class GroupCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_\-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    mfa_required: bool = False


class GroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    mfa_required: Optional[bool] = None


class GroupMember(BaseModel):
    id: str
    email: str
    username: str | None = None


class AddMember(BaseModel):
    user_id: str


class AssignGroupRole(BaseModel):
    role_id: str


__all__ = [
    "PermissionOut",
    "RoleOut",
    "RoleCreate",
    "RoleUpdate",
    "RolePermissions",
    "AssignRole",
    "TabPolicyOut",
    "TabRestrict",
    "AccessibleTab",
    "MePermissions",
    "GroupOut",
    "GroupCreate",
    "GroupUpdate",
    "GroupMember",
    "AddMember",
    "AssignGroupRole",
]
