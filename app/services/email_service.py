"""MailPit email service implementation."""

import logging
from email.message import EmailMessage

import aiosmtplib

logger = logging.getLogger(__name__)


class MailpitEmailService:
    """Adapter that delivers emails to MailPit over SMTP."""

    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host = host
        self._port = port
        self._sender = sender

    async def send_verification_code(self, to: str, code: str) -> None:
        """Send a verification code email to the given address."""
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = "Your verification code"
        message.set_content(
            f"Your verification code is: {code}\n\nIt expires in 1 minute."
        )

        try:
            await aiosmtplib.send(message, hostname=self._host, port=self._port)
            logger.info("Verification email sent to %s", to)
        except Exception:
            logger.error("Failed to send verification email to %s", to, exc_info=True)
            raise
