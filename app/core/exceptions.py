"""Domain exceptions raised by services and caught by API exception handlers."""


class EmailAlreadyRegisteredError(Exception):
    """Raised when a registration is attempted with an already-used email."""


class UserNotFoundError(Exception):
    """Raised when a user lookup returns no result."""


class InvalidCredentialsError(Exception):
    """Raised when email/password authentication fails."""
