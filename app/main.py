"""Application main module."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.users import router as users_router
from app.db.pool import close_pool, create_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool(dsn=os.environ["DATABASE_URL"])
    yield
    await close_pool()


app = FastAPI(
    title="User Registration API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users_router, prefix="/api/v1")

register_exception_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
