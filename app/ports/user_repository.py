"""Port (interface) for user persistence."""

from typing import Protocol
from uuid import UUID

from app.models.user import User


class UserRepositoryPort(Protocol):
    """Structural interface for user data access."""

    async def create(self, email: str, password_hash: str) -> User: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def set_active(self, user_id: UUID) -> None: ...
