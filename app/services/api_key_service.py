"""Service for API key management."""

import hashlib
import secrets
from typing import List, Optional, Tuple

from app.domain.models.api_key import ApiKey
from app.infrastructure.repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    """Service for managing API keys."""

    def __init__(self, api_key_repository: ApiKeyRepository):
        self.api_key_repository = api_key_repository

    def create_api_key(self, user_id: int, name: str) -> Tuple[ApiKey, str]:
        """
        Create a new API key for a user.

        Args:
            user_id: User ID
            name: Friendly name for the key

        Returns:
            Tuple of (ApiKey, plaintext_key)
            The plaintext key is only returned once and should be shown to the user.
        """
        # Generate a secure random key
        plaintext_key = f"mk_{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        key_hash = self._hash_key(plaintext_key)

        # Create the API key record
        api_key = self.api_key_repository.create(
            user_id=user_id,
            key=key_hash,
            name=name,
        )

        return api_key, plaintext_key

    def validate_api_key(self, plaintext_key: str) -> Optional[ApiKey]:
        """
        Validate an API key and return the associated ApiKey entity.

        Args:
            plaintext_key: The plaintext API key

        Returns:
            ApiKey if valid and active, None otherwise
        """
        key_hash = self._hash_key(plaintext_key)
        api_key = self.api_key_repository.get_by_key(key_hash)

        if not api_key or not api_key.is_active:
            return None

        # Update last used timestamp
        self.api_key_repository.update_last_used(api_key.id)

        return api_key

    def list_user_api_keys(self, user_id: int) -> List[ApiKey]:
        """
        List all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of ApiKey entities
        """
        return self.api_key_repository.list_by_user_id(user_id)

    def deactivate_api_key(self, api_key_id: int, user_id: int) -> bool:
        """
        Deactivate an API key.

        Args:
            api_key_id: API key ID
            user_id: User ID (for authorization)

        Returns:
            True if deactivated, False if not found or unauthorized
        """
        api_key = self.api_key_repository.get_by_id(api_key_id)
        if not api_key or api_key.user_id != user_id:
            return False

        self.api_key_repository.deactivate(api_key_id)
        return True

    def delete_api_key(self, api_key_id: int, user_id: int) -> bool:
        """
        Delete an API key.

        Args:
            api_key_id: API key ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        api_key = self.api_key_repository.get_by_id(api_key_id)
        if not api_key or api_key.user_id != user_id:
            return False

        self.api_key_repository.delete(api_key_id)
        return True

    def _hash_key(self, plaintext_key: str) -> str:
        """
        Hash an API key using SHA-256.

        Args:
            plaintext_key: The plaintext key

        Returns:
            Hashed key
        """
        return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()
