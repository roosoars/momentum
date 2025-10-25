"""API Key domain model for user API access."""

from datetime import datetime
from typing import Optional


class ApiKey:
    """
    ApiKey entity representing a user's API key for EA integration.

    Attributes:
        id: Unique identifier
        user_id: Reference to User
        key: The API key (stored hashed in database)
        name: Friendly name for the key
        is_active: Whether key is currently active
        last_used_at: Last time key was used
        created_at: Key creation timestamp
        updated_at: Last update timestamp
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        key: str,
        name: str,
        is_active: bool = True,
        last_used_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.key = key
        self.name = name
        self.is_active = is_active
        self.last_used_at = last_used_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} user_id={self.user_id} name={self.name}>"
