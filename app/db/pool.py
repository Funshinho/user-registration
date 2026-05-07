"""Asyncpg connection pool."""

import logging

import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)

_pool: Pool | None = None


async def create_pool(dsn: str) -> Pool:
    """Create the global connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    logger.info("Database pool created (min=2, max=10)")
    return _pool


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


def get_pool() -> Pool:
    """Return the active pool, raising if called before startup."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool
