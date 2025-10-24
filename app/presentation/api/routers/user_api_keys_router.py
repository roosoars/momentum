"""API router for user API key management."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_api_key_service
from app.domain.models.user import User
from app.presentation.api.routers.user_router import require_verified_user
from app.presentation.api.schemas.api_key_schemas import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysResponse,
)
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api/users/api-keys", tags=["user-api-keys"])


@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateApiKeyRequest,
    user: User = Depends(require_verified_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> CreateApiKeyResponse:
    """Create a new API key."""
    api_key, plaintext_key = api_key_service.create_api_key(
        user_id=user.id,
        name=request.name,
    )

    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plaintext_key,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ListApiKeysResponse)
async def list_api_keys(
    user: User = Depends(require_verified_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> ListApiKeysResponse:
    """List all API keys for current user."""
    api_keys = api_key_service.list_user_api_keys(user.id)

    items = []
    for api_key in api_keys:
        # Create a preview of the key (first 8 and last 4 chars)
        key_preview = f"{api_key.key[:8]}...{api_key.key[-4:]}"

        items.append(
            ApiKeyResponse(
                id=api_key.id,
                name=api_key.name,
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at,
                created_at=api_key.created_at,
                key_preview=key_preview,
            )
        )

    return ListApiKeysResponse(items=items, count=len(items))


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: int,
    user: User = Depends(require_verified_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> None:
    """Delete an API key."""
    success = api_key_service.delete_api_key(api_key_id, user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
