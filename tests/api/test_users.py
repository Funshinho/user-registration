"""Integration tests for user API endpoints."""

import base64
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from app.dependencies import get_user_service
from app.main import app
from app.schemas.users import UserResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user_response(**kwargs) -> UserResponse:
    return UserResponse(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "user@example.com"),
        is_active=kwargs.get("is_active", False),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )


def basic_auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def client(mock_service: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_user_service] = lambda: mock_service
    with patch("app.main.create_pool"), patch("app.main.close_pool"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/users — register
# ---------------------------------------------------------------------------


class TestRegisterUser:
    async def test_returns_201_on_success(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.register.return_value = make_user_response()

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )

        assert response.status_code == 201

    async def test_response_body_structure(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.register.return_value = make_user_response(
            email="user@example.com"
        )

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )
        body = response.json()

        assert body["email"] == "user@example.com"
        assert body["is_active"] is False
        assert "id" in body
        assert "created_at" in body

    async def test_response_exposes_no_password(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.register.return_value = make_user_response()

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )
        body = response.json()

        assert "password" not in body
        assert "password_hash" not in body

    async def test_returns_409_when_email_already_taken(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.register.side_effect = EmailAlreadyRegisteredError

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )

        assert response.status_code == 409

    async def test_returns_422_when_email_is_invalid(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "not-an-email", "password": "secret"}
        )

        assert response.status_code == 422

    async def test_returns_422_when_email_is_missing(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post("/api/v1/users", json={"password": "secret"})

        assert response.status_code == 422

    async def test_returns_422_when_password_is_missing(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com"}
        )

        assert response.status_code == 422

    async def test_returns_422_on_empty_body(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post("/api/v1/users", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/users/activate — activate
# ---------------------------------------------------------------------------


class TestActivateUser:
    async def test_returns_200_on_success(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.return_value = make_user_response(is_active=True)

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 200

    async def test_response_has_is_active_true(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.return_value = make_user_response(is_active=True)

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.json()["is_active"] is True

    async def test_passes_credentials_and_code_to_service(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.return_value = make_user_response(is_active=True)

        await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        mock_service.activate.assert_awaited_once_with(
            "user@example.com", "secret", "1234"
        )

    async def test_returns_401_without_auth_header(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post("/api/v1/users/activate", json={"code": "1234"})

        assert response.status_code == 401

    async def test_returns_401_on_invalid_credentials(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.side_effect = InvalidCredentialsError

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "wrongpass")},
        )

        assert response.status_code == 401

    async def test_returns_400_on_wrong_code(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.side_effect = InvalidVerificationCodeError

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 400

    async def test_returns_400_on_expired_code(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        mock_service.activate.side_effect = InvalidVerificationCodeError

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "0000"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 400

    async def test_returns_422_when_code_is_too_short(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_is_too_long(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12345"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_contains_letters(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12ab"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_is_missing(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422
