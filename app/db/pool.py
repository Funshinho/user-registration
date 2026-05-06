"""Asyncpg connection pool."""

import asyncpg
from asyncpg import Pool

_pool: Pool | None = None


async def create_pool(dsn: str) -> Pool:
    """Create the global connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> Pool:
    """Return the active pool, raising if called before startup."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool
