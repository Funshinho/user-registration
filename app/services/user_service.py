"""User registration and activation business logic."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from app.core.security import hash_password, verify_password
from app.ports.email_service import EmailServicePort
from app.ports.user_repository import UserRepositoryPort
from app.ports.verification_code_repository import VerificationCodeRepositoryPort
from app.schemas.users import UserResponse

logger = logging.getLogger(__name__)

_CODE_TTL_SECONDS = 60


class UserService:
    """Orchestrates user registration and account activation."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        code_repo: VerificationCodeRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self._user_repo = user_repo
        self._code_repo = code_repo
        self._email_service = email_service

    async def register(self, email: str, password: str) -> UserResponse:
        """Create an inactive user, generate a verification code, and send it by email."""
        if await self._user_repo.get_by_email(email) is not None:
            logger.warning(
                "Registration attempt with already-registered email: %s", email
            )
            raise EmailAlreadyRegisteredError(email)

        user = await self._user_repo.create(email, hash_password(password))

        code = f"{secrets.randbelow(10000):04d}"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=_CODE_TTL_SECONDS)
        await self._code_repo.create(user.id, code, expires_at)
        await self._email_service.send_verification_code(user.email, code)

        logger.info("User registered: %s (id=%s)", user.email, user.id)
        return UserResponse.model_validate(user.model_dump())

    async def activate(self, email: str, password: str, code: str) -> UserResponse:
        """Verify Basic Auth credentials and the 4-digit code, then activate the account."""
        user = await self._user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            logger.warning("Activation failed: invalid credentials")
            raise InvalidCredentialsError

        verification = await self._code_repo.get_active_by_user(user.id)
        if verification is None or verification.code.strip() != code:
            logger.warning(
                "Activation failed: invalid or expired code (user_id=%s)", user.id
            )
            raise InvalidVerificationCodeError

        await self._code_repo.mark_used(verification.id)
        await self._user_repo.set_active(user.id)

        logger.info("Account activated: %s (id=%s)", user.email, user.id)
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=True,
            created_at=user.created_at,
        )
