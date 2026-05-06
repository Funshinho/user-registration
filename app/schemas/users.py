"""Pydantic schemas for user API request and response payloads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Registration request payload."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user representation."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
