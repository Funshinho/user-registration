"""UserService unit tests"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import verify_password
from app.models.user import User
from app.schemas.users import UserResponse
from app.services.user_service import UserService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(
    email: str = "user@example.com",
    is_active: bool = False,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash="$2b$12$hashed",
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo() -> AsyncMock:
    mock = AsyncMock()
    mock.get_by_email.return_value = None
    mock.create.return_value = make_user()
    return mock


@pytest.fixture
def service(repo: AsyncMock) -> UserService:
    return UserService(user_repo=repo)


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_returns_user_response(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        result = await service.register("user@example.com", "secret123")

        assert isinstance(result, UserResponse)
        assert result.email == "user@example.com"

    async def test_new_user_is_inactive(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        result = await service.register("user@example.com", "secret123")

        assert result.is_active is False

    async def test_password_is_hashed_before_persistence(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        plain = "secret123"
        await service.register("user@example.com", plain)

        _, stored_hash = repo.create.call_args.args
        assert stored_hash != plain
        assert verify_password(plain, stored_hash)

    async def test_raises_when_email_already_registered(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        repo.get_by_email.return_value = make_user()

        with pytest.raises(EmailAlreadyRegisteredError):
            await service.register("user@example.com", "secret123")

    async def test_create_not_called_when_email_exists(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        repo.get_by_email.return_value = make_user()

        with pytest.raises(EmailAlreadyRegisteredError):
            await service.register("user@example.com", "secret123")

        repo.create.assert_not_called()

    async def test_response_exposes_no_password(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        result = await service.register("user@example.com", "secret123")

        assert not hasattr(result, "password_hash")
        assert not hasattr(result, "password")

    async def test_get_by_email_called_with_provided_email(
        self, service: UserService, repo: AsyncMock
    ) -> None:
        email = "user@example.com"
        await service.register(email, "secret123")

        repo.get_by_email.assert_awaited_once_with(email)
