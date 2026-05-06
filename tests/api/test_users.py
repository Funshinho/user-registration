"""Integration tests for user API endpoints."""

import base64
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from app.db.pool import close_pool, create_pool, get_pool
from app.dependencies import get_email_service, get_user_service
from app.main import app
from app.schemas.users import UserResponse

# When DATABASE_URL is set the suite runs against a real PostgreSQL instance.
# Without it (local dev, no Docker) the service layer is replaced with an AsyncMock.
_REAL_DB = bool(os.getenv("DATABASE_URL"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def basic_auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def make_user_response(**kwargs) -> UserResponse:
    return UserResponse(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "user@example.com"),
        is_active=kwargs.get("is_active", False),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_email_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def client(
    mock_service: AsyncMock, mock_email_service: AsyncMock
) -> AsyncGenerator[AsyncClient, None]:
    if _REAL_DB:
        # ASGITransport does not fire the ASGI lifespan protocol, so manage the
        # pool explicitly instead of relying on the app's lifespan handler.
        app.dependency_overrides[get_email_service] = lambda: mock_email_service
        await create_pool(dsn=os.environ["DATABASE_URL"])
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                try:
                    yield c
                finally:
                    async with get_pool().acquire() as conn:
                        await conn.execute("TRUNCATE verification_codes, users CASCADE")
        finally:
            await close_pool()
            app.dependency_overrides.clear()
    else:
        app.dependency_overrides[get_user_service] = lambda: mock_service
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
        if not _REAL_DB:
            mock_service.register.return_value = make_user_response()

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )

        assert response.status_code == 201

    async def test_response_body_structure(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        if not _REAL_DB:
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
        if not _REAL_DB:
            mock_service.register.return_value = make_user_response()

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )
        body = response.json()

        assert "password" not in body
        assert "password_hash" not in body

    @pytest.mark.skipif(not _REAL_DB, reason="requires real database")
    async def test_sends_verification_email(
        self, client: AsyncClient, mock_email_service: AsyncMock
    ) -> None:
        await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )

        mock_email_service.send_verification_code.assert_awaited_once()
        email, code = mock_email_service.send_verification_code.call_args.args
        assert email == "user@example.com"
        assert len(code) == 4 and code.isdigit()

    async def test_returns_409_when_email_already_taken(
        self, client: AsyncClient, mock_service: AsyncMock
    ) -> None:
        if _REAL_DB:
            await client.post(
                "/api/v1/users",
                json={"email": "user@example.com", "password": "secret"},
            )
        else:
            mock_service.register.side_effect = EmailAlreadyRegisteredError

        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com", "password": "secret"}
        )

        assert response.status_code == 409

    async def test_returns_422_when_email_is_invalid(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "not-an-email", "password": "secret"}
        )

        assert response.status_code == 422

    async def test_returns_422_when_email_is_missing(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/users", json={"password": "secret"})

        assert response.status_code == 422

    async def test_returns_422_when_password_is_missing(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "user@example.com"}
        )

        assert response.status_code == 422

    async def test_returns_422_on_empty_body(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/users", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/users/activate — activate
# ---------------------------------------------------------------------------


class TestActivateUser:
    async def _register_and_get_code(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
        email: str = "user@example.com",
        pwd: str = "secret",
    ) -> str:
        if _REAL_DB:
            await client.post("/api/v1/users", json={"email": email, "password": pwd})
            _, code = mock_email_service.send_verification_code.call_args.args
            return code
        else:
            mock_service.register.return_value = make_user_response(email=email)
            await client.post("/api/v1/users", json={"email": email, "password": pwd})
            return "1234"

    async def test_returns_200_on_success(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
    ) -> None:
        code = await self._register_and_get_code(
            client, mock_service, mock_email_service
        )
        if not _REAL_DB:
            mock_service.activate.return_value = make_user_response(is_active=True)

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": code},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 200

    async def test_response_has_is_active_true(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
    ) -> None:
        code = await self._register_and_get_code(
            client, mock_service, mock_email_service
        )
        if not _REAL_DB:
            mock_service.activate.return_value = make_user_response(is_active=True)

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": code},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.json()["is_active"] is True

    async def test_returns_401_without_auth_header(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/users/activate", json={"code": "1234"})

        assert response.status_code == 401

    async def test_returns_401_on_invalid_credentials(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
    ) -> None:
        await self._register_and_get_code(client, mock_service, mock_email_service)
        if not _REAL_DB:
            mock_service.activate.side_effect = InvalidCredentialsError

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "wrongpass")},
        )

        assert response.status_code == 401

    async def test_returns_400_on_wrong_code(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
    ) -> None:
        code = await self._register_and_get_code(
            client, mock_service, mock_email_service
        )
        if _REAL_DB:
            wrong_code = "0000" if code != "0000" else "1111"
        else:
            mock_service.activate.side_effect = InvalidVerificationCodeError
            wrong_code = "0000"

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": wrong_code},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 400

    @pytest.mark.skipif(not _REAL_DB, reason="requires real database")
    async def test_returns_400_on_expired_code(
        self,
        client: AsyncClient,
        mock_service: AsyncMock,
        mock_email_service: AsyncMock,
    ) -> None:
        await self._register_and_get_code(client, mock_service, mock_email_service)

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE verification_codes SET expires_at = NOW() - INTERVAL '1 minute'"
            )

        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "1234"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 400

    async def test_returns_422_when_code_is_too_short(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_is_too_long(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12345"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_contains_letters(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={"code": "12ab"},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422

    async def test_returns_422_when_code_is_missing(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users/activate",
            json={},
            headers={"Authorization": basic_auth("user@example.com", "secret")},
        )

        assert response.status_code == 422
