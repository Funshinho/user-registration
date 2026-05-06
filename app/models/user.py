"""Internal domain model for a user row from the database."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    """Internal user model."""

    id: UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
