"""Port (interface) for verification code persistence."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.models.verification_code import VerificationCode


class VerificationCodeRepositoryPort(Protocol):
    """Structural interface for verification code data access."""

    async def create(
        self, user_id: UUID, code: str, expires_at: datetime
    ) -> VerificationCode: ...

    async def get_active_by_user(self, user_id: UUID) -> VerificationCode | None: ...

    async def mark_used(self, code_id: UUID) -> None: ...
