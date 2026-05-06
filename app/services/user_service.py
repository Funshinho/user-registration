"""User registration business logic."""

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import hash_password
from app.ports.user_repository import UserRepositoryPort
from app.schemas.users import UserResponse


class UserService:
    """Orchestrates user registration."""

    def __init__(self, user_repo: UserRepositoryPort) -> None:
        self._repo = user_repo

    async def register(self, email: str, password: str) -> UserResponse:
        """Create a new inactive user after verifying the email is not already taken."""
        if await self._repo.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)

        user = await self._repo.create(email, hash_password(password))
        return UserResponse.model_validate(user.model_dump())
