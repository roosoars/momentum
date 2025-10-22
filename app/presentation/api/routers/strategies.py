from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....application.services.strategy_service import StrategyService
from ....domain.models import Strategy, StrategySignal, User
from ....core.dependencies import get_strategy_service
from ...api.dependencies import require_admin_user
from ...api.schemas.strategy import (
    StrategyAssignChannelPayload,
    StrategyCreatePayload,
    StrategyRenamePayload,
)

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


@router.get("")
async def list_strategies(
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    strategies = await service.list_strategies()
    items: List[Dict[str, Any]] = []
    for strategy in strategies:
        last_signal: Optional[StrategySignal] = None
        signals = await service.get_signals(strategy.id, limit=1)
        if signals:
            last_signal = signals[0]
        items.append(_serialize_strategy(strategy, last_signal))
    return {"items": items, "count": len(items)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_strategy(
    payload: StrategyCreatePayload,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.create_strategy(
            name=payload.name,
            channel_identifier=payload.channel_identifier,
            activate=payload.activate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.patch("/{strategy_id}")
async def rename_strategy(
    strategy_id: int,
    payload: StrategyRenamePayload,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.rename_strategy(strategy_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/channel")
async def assign_strategy_channel(
    strategy_id: int,
    payload: StrategyAssignChannelPayload,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.assign_channel(strategy_id, payload.channel_identifier)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: int,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.activate_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: int,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.deactivate_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/pause")
async def pause_strategy(
    strategy_id: int,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.pause_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/resume")
async def resume_strategy(
    strategy_id: int,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    try:
        strategy = await service.resume_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_strategy(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> None:
    try:
        await service.delete_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{strategy_id}/signals")
async def list_strategy_signals(
    strategy_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    newer_than: Optional[str] = Query(default=None),
    _: User = Depends(require_admin_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    since_dt: Optional[datetime] = None
    if newer_than:
        try:
            since_dt = datetime.fromisoformat(newer_than)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parâmetro newer_than inválido.") from exc
    try:
        signals = await service.get_signals(strategy_id, limit=limit, newer_than=since_dt)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "items": [_serialize_signal(item) for item in signals],
        "count": len(signals),
    }


def _serialize_strategy(strategy: Strategy, last_signal: Optional[StrategySignal] = None) -> Dict[str, Any]:
    status_label = "inactive"
    if strategy.is_active and strategy.is_paused:
        status_label = "paused"
    elif strategy.is_active:
        status_label = "active"
    payload: Dict[str, Any] = {
        "id": strategy.id,
        "name": strategy.name,
        "channel_identifier": strategy.channel_identifier,
        "channel_id": strategy.channel_id,
        "channel_title": strategy.channel_title,
        "channel_linked_at": strategy.channel_linked_at.isoformat() if strategy.channel_linked_at else None,
        "is_active": strategy.is_active,
        "is_paused": strategy.is_paused,
        "status": status_label,
        "created_at": strategy.created_at.replace(microsecond=0).isoformat(),
        "updated_at": strategy.updated_at.replace(microsecond=0).isoformat(),
    }
    if last_signal:
        payload["last_signal"] = _serialize_signal(last_signal)
    return payload


def _serialize_signal(signal: StrategySignal) -> Dict[str, Any]:
    return {
        "id": signal.id,
        "strategy_id": signal.strategy_id,
        "channel_id": signal.channel_id,
        "telegram_message_id": signal.telegram_message_id,
        "raw_message": signal.raw_message,
        "parsed_payload": signal.parsed_payload,
        "status": signal.status,
        "error": signal.error,
        "received_at": signal.received_at.replace(microsecond=0).isoformat(),
        "processed_at": signal.processed_at.replace(microsecond=0).isoformat(),
    }
