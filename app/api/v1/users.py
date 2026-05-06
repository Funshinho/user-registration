"""User registration endpoints."""

from fastapi import APIRouter

from app.dependencies import UserServiceDep
from app.schemas.users import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", status_code=201)
async def register_user(body: UserCreate, service: UserServiceDep) -> UserResponse:
    """Register a new user account."""
    return await service.register(body.email, body.password)
