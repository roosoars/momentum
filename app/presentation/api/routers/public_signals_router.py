"""Public API router for signals (authenticated via API key)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_api_key_service,
    get_persistence_gateway,
    get_subscription_service,
)
from app.domain.models.api_key import ApiKey
from app.domain.ports.persistence import PersistenceGateway
from app.services.api_key_service import ApiKeyService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/signals", tags=["signals"])


def get_api_key_from_header(
    x_api_key: str = "",
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> ApiKey:
    """Validate API key from X-API-Key header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    api_key = api_key_service.validate_api_key(x_api_key)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


def require_active_subscription(
    api_key: ApiKey = Depends(get_api_key_from_header),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> ApiKey:
    """Require user to have an active subscription."""
    has_active = subscription_service.has_active_subscription(api_key.user_id)

    if not has_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to access signals",
        )

    return api_key


@router.get("")
async def get_signals(
    limit: int = Query(default=100, le=1000, description="Maximum number of signals to return"),
    strategy_id: Optional[int] = Query(default=None, description="Filter by strategy ID"),
    status_filter: str = Query(default="parsed", description="Filter by signal status"),
    api_key: ApiKey = Depends(require_active_subscription),
    persistence: PersistenceGateway = Depends(get_persistence_gateway),
) -> dict:
    """
    Get signals for the authenticated user.

    Requires:
    - Valid API key in X-API-Key header
    - Active subscription

    Returns signals in descending order by processed_at (newest first).
    """
    try:
        # Get all strategies to get their signals
        strategies = persistence.list_strategies()

        all_signals = []

        for strategy in strategies:
            # If strategy_id filter is provided, only fetch from that strategy
            if strategy_id is not None and strategy.id != strategy_id:
                continue

            signals = persistence.list_signals(strategy.id, limit=limit)

            for signal in signals:
                # Filter by status
                if signal.status != status_filter:
                    continue

                all_signals.append({
                    "id": signal.id,
                    "strategy_id": signal.strategy_id,
                    "strategy_name": strategy.name,
                    "channel_id": signal.channel_id,
                    "telegram_message_id": signal.telegram_message_id,
                    "raw_message": signal.raw_message,
                    "parsed_payload": signal.parsed_payload,
                    "status": signal.status,
                    "error": signal.error,
                    "received_at": signal.received_at.isoformat() if signal.received_at else None,
                    "processed_at": signal.processed_at.isoformat() if signal.processed_at else None,
                })

        # Sort by processed_at descending
        all_signals.sort(
            key=lambda x: x["processed_at"] or "",
            reverse=True,
        )

        # Apply overall limit
        all_signals = all_signals[:limit]

        return {
            "items": all_signals,
            "count": len(all_signals),
            "limit": limit,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch signals: {str(e)}",
        )


@router.get("/latest")
async def get_latest_signal(
    strategy_id: Optional[int] = Query(default=None, description="Filter by strategy ID"),
    api_key: ApiKey = Depends(require_active_subscription),
    persistence: PersistenceGateway = Depends(get_persistence_gateway),
) -> dict:
    """
    Get the latest signal.

    Requires:
    - Valid API key in X-API-Key header
    - Active subscription

    Returns the most recent parsed signal.
    """
    try:
        strategies = persistence.list_strategies()

        latest_signal = None
        latest_strategy_name = None

        for strategy in strategies:
            if strategy_id is not None and strategy.id != strategy_id:
                continue

            signals = persistence.list_signals(strategy.id, limit=1)

            for signal in signals:
                if signal.status != "parsed":
                    continue

                if not latest_signal or (signal.processed_at and signal.processed_at > latest_signal.processed_at):
                    latest_signal = signal
                    latest_strategy_name = strategy.name

        if not latest_signal:
            return {
                "signal": None,
                "message": "No signals found",
            }

        return {
            "signal": {
                "id": latest_signal.id,
                "strategy_id": latest_signal.strategy_id,
                "strategy_name": latest_strategy_name,
                "channel_id": latest_signal.channel_id,
                "telegram_message_id": latest_signal.telegram_message_id,
                "raw_message": latest_signal.raw_message,
                "parsed_payload": latest_signal.parsed_payload,
                "status": latest_signal.status,
                "error": latest_signal.error,
                "received_at": latest_signal.received_at.isoformat() if latest_signal.received_at else None,
                "processed_at": latest_signal.processed_at.isoformat() if latest_signal.processed_at else None,
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest signal: {str(e)}",
        )
