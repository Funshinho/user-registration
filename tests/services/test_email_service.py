"""Unit tests for MailpitEmailService."""

from email.message import EmailMessage
from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from app.services.email_service import MailpitEmailService

SMTP_HOST = "localhost"
SMTP_PORT = 1025
SENDER = "no-reply@dailymotion.com"


@pytest.fixture
def service() -> MailpitEmailService:
    return MailpitEmailService(host=SMTP_HOST, port=SMTP_PORT, sender=SENDER)


@pytest.fixture
def mock_smtp_send():
    with patch(
        "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
    ) as mock:
        yield mock


class TestSendVerificationCode:
    async def test_sends_to_correct_recipient(
        self, service: MailpitEmailService, mock_smtp_send: AsyncMock
    ) -> None:
        await service.send_verification_code("user@example.com", "4242")

        message: EmailMessage = mock_smtp_send.call_args.args[0]
        assert message["To"] == "user@example.com"

    async def test_sends_from_configured_sender(
        self, service: MailpitEmailService, mock_smtp_send: AsyncMock
    ) -> None:
        await service.send_verification_code("user@example.com", "4242")

        message: EmailMessage = mock_smtp_send.call_args.args[0]
        assert message["From"] == SENDER

    async def test_message_contains_code(
        self, service: MailpitEmailService, mock_smtp_send: AsyncMock
    ) -> None:
        await service.send_verification_code("user@example.com", "4242")

        message: EmailMessage = mock_smtp_send.call_args.args[0]
        assert "4242" in message.get_body().get_content()

    async def test_uses_configured_smtp_host_and_port(
        self, service: MailpitEmailService, mock_smtp_send: AsyncMock
    ) -> None:
        await service.send_verification_code("user@example.com", "4242")

        kwargs = mock_smtp_send.call_args.kwargs
        assert kwargs["hostname"] == SMTP_HOST
        assert kwargs["port"] == SMTP_PORT

    async def test_smtp_error_propagates(
        self, service: MailpitEmailService, mock_smtp_send: AsyncMock
    ) -> None:
        mock_smtp_send.side_effect = aiosmtplib.SMTPException("connection refused")

        with pytest.raises(aiosmtplib.SMTPException):
            await service.send_verification_code("user@example.com", "4242")
