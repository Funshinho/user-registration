"""Pydantic schemas for user API request and response payloads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Registration request payload."""

    email: EmailStr
    password: str


class ActivateRequest(BaseModel):
    """Activation request payload."""

    code: str = Field(pattern=r"^\d{4}$")


class UserResponse(BaseModel):
    """Public user representation."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
