"""User domain model for client authentication and management."""

from datetime import datetime
from typing import Optional


class User:
    """
    User entity representing a client account.

    Attributes:
        id: Unique identifier
        email: User email address (unique)
        password_hash: Hashed password
        is_verified: Whether email has been verified
        verification_token: Token for email verification
        verification_expires_at: Expiration timestamp for verification token
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    def __init__(
        self,
        id: int,
        email: str,
        password_hash: str,
        is_verified: bool = False,
        verification_token: Optional[str] = None,
        verification_expires_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.is_verified = is_verified
        self.verification_token = verification_token
        self.verification_expires_at = verification_expires_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} verified={self.is_verified}>"
