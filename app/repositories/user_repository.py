"""Data access layer for the users table."""

from uuid import UUID

import asyncpg

from app.models.user import User


class UserRepository:
    """Handles all database operations for the users table."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, email: str, password_hash: str) -> User:
        """Insert a new inactive user and return the created row."""
        row = await self._conn.fetchrow(
            """
            INSERT INTO users (email, password)
            VALUES ($1, $2)
            RETURNING id, email, password AS password_hash, is_active, created_at
            """,
            email,
            password_hash,
        )
        return User(**dict(row))

    async def get_by_email(self, email: str) -> User | None:
        """Return the user matching the given email, or None."""
        row = await self._conn.fetchrow(
            "SELECT id, email, password AS password_hash, is_active, created_at FROM users WHERE email = $1",
            email,
        )
        return User(**dict(row)) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user matching the given id, or None."""
        row = await self._conn.fetchrow(
            "SELECT id, email, password AS password_hash, is_active, created_at FROM users WHERE id = $1",
            user_id,
        )
        return User(**dict(row)) if row else None

    async def set_active(self, user_id: UUID) -> None:
        """Mark the user account as active."""
        await self._conn.execute(
            "UPDATE users SET is_active = TRUE WHERE id = $1",
            user_id,
        )
