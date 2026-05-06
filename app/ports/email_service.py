"""Port (interface) for the email third-party service."""

from typing import Protocol


class EmailServicePort(Protocol):
    """Structural interface for sending transactional emails."""

    async def send_verification_code(self, to: str, code: str) -> None: ...
