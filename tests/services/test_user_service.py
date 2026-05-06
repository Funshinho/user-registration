"""UserService unit tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.schemas.users import UserResponse
from app.services.user_service import UserService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLAIN_PASSWORD = "secret123"
_HASHED_PASSWORD = hash_password(_PLAIN_PASSWORD)


def make_user(
    email: str = "user@example.com",
    is_active: bool = False,
    password_hash: str = _HASHED_PASSWORD,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash=password_hash,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


def make_verification_code(
    user_id: UUID | None = None,
    code: str = "1234",
    expired: bool = False,
) -> VerificationCode:
    delta = timedelta(seconds=-1) if expired else timedelta(seconds=60)
    return VerificationCode(
        id=uuid4(),
        user_id=user_id or uuid4(),
        code=code,
        expires_at=datetime.now(timezone.utc) + delta,
        used_at=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_repo() -> AsyncMock:
    mock = AsyncMock()
    mock.get_by_email.return_value = None
    mock.create.return_value = make_user()
    return mock


@pytest.fixture
def code_repo() -> AsyncMock:
    mock = AsyncMock()
    mock.create.return_value = make_verification_code()
    mock.get_active_by_user.return_value = make_verification_code()
    return mock


@pytest.fixture
def email_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    user_repo: AsyncMock, code_repo: AsyncMock, email_service: AsyncMock
) -> UserService:
    return UserService(
        user_repo=user_repo, code_repo=code_repo, email_service=email_service
    )


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_returns_user_response(self, service: UserService) -> None:
        result = await service.register("user@example.com", _PLAIN_PASSWORD)

        assert isinstance(result, UserResponse)
        assert result.email == "user@example.com"

    async def test_new_user_is_inactive(self, service: UserService) -> None:
        result = await service.register("user@example.com", _PLAIN_PASSWORD)

        assert result.is_active is False

    async def test_password_is_hashed_before_persistence(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        await service.register("user@example.com", _PLAIN_PASSWORD)

        _, stored_hash = user_repo.create.call_args.args
        assert stored_hash != _PLAIN_PASSWORD
        assert verify_password(_PLAIN_PASSWORD, stored_hash)

    async def test_raises_when_email_already_registered(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = make_user()

        with pytest.raises(EmailAlreadyRegisteredError):
            await service.register("user@example.com", _PLAIN_PASSWORD)

    async def test_create_not_called_when_email_exists(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = make_user()

        with pytest.raises(EmailAlreadyRegisteredError):
            await service.register("user@example.com", _PLAIN_PASSWORD)

        user_repo.create.assert_not_called()

    async def test_verification_code_is_stored(
        self, service: UserService, code_repo: AsyncMock
    ) -> None:
        await service.register("user@example.com", _PLAIN_PASSWORD)

        code_repo.create.assert_awaited_once()

    async def test_verification_code_is_four_digits(
        self, service: UserService, code_repo: AsyncMock
    ) -> None:
        await service.register("user@example.com", _PLAIN_PASSWORD)

        _, code, _ = code_repo.create.call_args.args
        assert len(code) == 4
        assert code.isdigit()

    async def test_email_sent_after_user_created(
        self, service: UserService, email_service: AsyncMock
    ) -> None:
        await service.register("user@example.com", _PLAIN_PASSWORD)

        email_service.send_verification_code.assert_awaited_once()

    async def test_email_sent_to_registered_address(
        self, service: UserService, email_service: AsyncMock
    ) -> None:
        await service.register("user@example.com", _PLAIN_PASSWORD)

        to, _ = email_service.send_verification_code.call_args.args
        assert to == "user@example.com"

    async def test_response_exposes_no_password(self, service: UserService) -> None:
        result = await service.register("user@example.com", _PLAIN_PASSWORD)

        assert not hasattr(result, "password_hash")
        assert not hasattr(result, "password")


# ---------------------------------------------------------------------------
# activate()
# ---------------------------------------------------------------------------


class TestActivate:
    async def test_returns_active_user_response(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user = make_user()
        user_repo.get_by_email.return_value = user
        code_repo.get_active_by_user.return_value = make_verification_code(
            user_id=user.id
        )

        result = await service.activate(user.email, _PLAIN_PASSWORD, "1234")

        assert isinstance(result, UserResponse)
        assert result.is_active is True

    async def test_marks_code_as_used_on_success(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user = make_user()
        verification = make_verification_code(user_id=user.id)
        user_repo.get_by_email.return_value = user
        code_repo.get_active_by_user.return_value = verification

        await service.activate(user.email, _PLAIN_PASSWORD, "1234")

        code_repo.mark_used.assert_awaited_once_with(verification.id)

    async def test_sets_user_active_on_success(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user = make_user()
        user_repo.get_by_email.return_value = user
        code_repo.get_active_by_user.return_value = make_verification_code(
            user_id=user.id
        )

        await service.activate(user.email, _PLAIN_PASSWORD, "1234")

        user_repo.set_active.assert_awaited_once_with(user.id)

    async def test_raises_when_user_not_found(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidCredentialsError):
            await service.activate("unknown@example.com", _PLAIN_PASSWORD, "1234")

    async def test_raises_when_password_is_wrong(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = make_user()

        with pytest.raises(InvalidCredentialsError):
            await service.activate("user@example.com", "wrongpassword", "1234")

    async def test_wrong_user_and_wrong_password_raise_same_error(
        self, service: UserService, user_repo: AsyncMock
    ) -> None:
        """Both cases raise InvalidCredentialsError to avoid leaking whether the email exists."""
        user_repo.get_by_email.return_value = None
        with pytest.raises(InvalidCredentialsError):
            await service.activate("ghost@example.com", "any", "1234")

        user_repo.get_by_email.return_value = make_user()
        with pytest.raises(InvalidCredentialsError):
            await service.activate("user@example.com", "wrongpassword", "1234")

    async def test_raises_when_no_active_code(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = make_user()
        code_repo.get_active_by_user.return_value = None

        with pytest.raises(InvalidVerificationCodeError):
            await service.activate("user@example.com", _PLAIN_PASSWORD, "1234")

    async def test_raises_when_code_does_not_match(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user = make_user()
        user_repo.get_by_email.return_value = user
        code_repo.get_active_by_user.return_value = make_verification_code(
            user_id=user.id, code="9999"
        )

        with pytest.raises(InvalidVerificationCodeError):
            await service.activate(user.email, _PLAIN_PASSWORD, "1234")

    async def test_mark_used_not_called_on_wrong_code(
        self, service: UserService, user_repo: AsyncMock, code_repo: AsyncMock
    ) -> None:
        user = make_user()
        user_repo.get_by_email.return_value = user
        code_repo.get_active_by_user.return_value = make_verification_code(
            user_id=user.id, code="9999"
        )

        with pytest.raises(InvalidVerificationCodeError):
            await service.activate(user.email, _PLAIN_PASSWORD, "1234")

        code_repo.mark_used.assert_not_called()
