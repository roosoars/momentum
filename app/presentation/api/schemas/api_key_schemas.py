"""Pydantic schemas for API key endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateApiKeyRequest(BaseModel):
    """Request schema for creating an API key."""

    name: str


class CreateApiKeyResponse(BaseModel):
    """Response schema for creating an API key."""

    id: int
    name: str
    key: str
    created_at: datetime
    message: str = "API key created successfully. Save this key securely, it won't be shown again."


class ApiKeyResponse(BaseModel):
    """Response schema for API key data (without the actual key)."""

    id: int
    name: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    key_preview: str  # First and last 4 characters


class ListApiKeysResponse(BaseModel):
    """Response schema for listing API keys."""

    items: list[ApiKeyResponse]
    count: int
