"""FastAPI dependency providers for DB connections and services."""

import os
from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Depends

from app.db.pool import get_pool
from app.repositories.user_repository import UserRepository
from app.repositories.verification_code_repository import VerificationCodeRepository
from app.services.email_service import MailpitEmailService
from app.services.user_service import UserService


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a connection from the pool and release it after the request."""
    async with get_pool().acquire() as conn:
        yield conn


def get_email_service() -> MailpitEmailService:
    """Build the email service from environment configuration."""
    return MailpitEmailService(
        host=os.environ["SMTP_HOST"],
        port=int(os.environ["SMTP_PORT"]),
        sender=os.environ["EMAIL_FROM"],
    )


DbConnection = Annotated[asyncpg.Connection, Depends(get_db_connection)]
EmailServiceDep = Annotated[MailpitEmailService, Depends(get_email_service)]


def get_user_service(conn: DbConnection, email_service: EmailServiceDep) -> UserService:
    """Build a UserService wired to the request-scoped DB connection and email service."""
    return UserService(
        user_repo=UserRepository(conn),
        code_repo=VerificationCodeRepository(conn),
        email_service=email_service,
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
