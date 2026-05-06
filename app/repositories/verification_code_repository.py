"""Data access layer for the verification_codes table."""

from datetime import datetime
from uuid import UUID

import asyncpg

from app.models.verification_code import VerificationCode


class VerificationCodeRepository:
    """Handles all database operations for the verification_codes table."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self, user_id: UUID, code: str, expires_at: datetime
    ) -> VerificationCode:
        """Insert a new verification code and return the created row."""
        row = await self._conn.fetchrow(
            """
            INSERT INTO verification_codes (user_id, code, expires_at)
            VALUES ($1, $2, $3)
            RETURNING id, user_id, code, expires_at, used_at
            """,
            user_id,
            code,
            expires_at,
        )
        return VerificationCode(**dict(row))

    async def get_active_by_user(self, user_id: UUID) -> VerificationCode | None:
        """Return the most recent unused, non-expired code for a user, or None."""
        row = await self._conn.fetchrow(
            """
            SELECT id, user_id, code, expires_at, used_at
            FROM verification_codes
            WHERE user_id = $1
              AND used_at IS NULL
              AND expires_at > NOW()
            ORDER BY expires_at DESC
            LIMIT 1
            """,
            user_id,
        )
        return VerificationCode(**dict(row)) if row else None

    async def mark_used(self, code_id: UUID) -> None:
        """Set used_at to the current timestamp for the given code."""
        await self._conn.execute(
            "UPDATE verification_codes SET used_at = NOW() WHERE id = $1",
            code_id,
        )
