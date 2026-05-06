"""Password hashing utilities using bcrypt."""

import bcrypt


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of a plaintext password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext password matches the stored hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())
