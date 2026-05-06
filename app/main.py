"""Application main module."""

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialise DB connection pool, etc.
    yield
    # shutdown: close DB connection pool, etc.


app = FastAPI(
    title="User Registration API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
