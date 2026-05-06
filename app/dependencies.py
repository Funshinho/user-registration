"""FastAPI dependency providers for DB connections and services."""

from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Depends

from app.db.pool import get_pool
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a connection from the pool and release it after the request."""
    async with get_pool().acquire() as conn:
        yield conn


DbConnection = Annotated[asyncpg.Connection, Depends(get_db_connection)]


def get_user_service(conn: DbConnection) -> UserService:
    """Build a UserService wired to the request-scoped DB connection."""
    return UserService(user_repo=UserRepository(conn))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
