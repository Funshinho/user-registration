"""FastAPI exception handlers mapping domain exceptions to HTTP responses."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all domain exception handlers to the application."""

    @app.exception_handler(EmailAlreadyRegisteredError)
    async def email_already_registered_handler(
        _request, _exc: EmailAlreadyRegisteredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"detail": "Email already registered"}
        )

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        _request, _exc: InvalidCredentialsError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    @app.exception_handler(InvalidVerificationCodeError)
    async def invalid_verification_code_handler(
        _request, _exc: InvalidVerificationCodeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400, content={"detail": "Invalid or expired verification code"}
        )
