"""Internal domain model for a verification_codes row."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VerificationCode(BaseModel):
    """Internal verification code model."""

    id: UUID
    user_id: UUID
    code: str
    expires_at: datetime
    used_at: datetime | None
