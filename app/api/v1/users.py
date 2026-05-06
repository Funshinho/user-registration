"""User registration and activation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.dependencies import UserServiceDep
from app.schemas.users import ActivateRequest, UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
_basic = HTTPBasic()

BasicAuth = Annotated[HTTPBasicCredentials, Depends(_basic)]


@router.post("", status_code=201)
async def register_user(body: UserCreate, service: UserServiceDep) -> UserResponse:
    """Register a new user account."""
    return await service.register(body.email, body.password)


@router.post("/activate", status_code=200)
async def activate_user(
    credentials: BasicAuth,
    body: ActivateRequest,
    service: UserServiceDep,
) -> UserResponse:
    """Activate an account using Basic Auth credentials and the emailed 4-digit code."""
    return await service.activate(credentials.username, credentials.password, body.code)
