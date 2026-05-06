"""MailPit email service implementation."""

from email.message import EmailMessage

import aiosmtplib


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

        await aiosmtplib.send(message, hostname=self._host, port=self._port)
