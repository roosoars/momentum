from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from ....application.services.channel_service import ChannelService
from ....core.dependencies import get_channel_service
from ...api.schemas.channel import ChannelConfig

router = APIRouter(prefix="/api/config", tags=["Channel Configuration"])


@router.get("")
async def get_config(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    return channel_service.current_configuration()


@router.post("/channel", status_code=status.HTTP_202_ACCEPTED)
async def update_channel(
    payload: ChannelConfig,
    channel_service: ChannelService = Depends(get_channel_service),
) -> Dict[str, Any]:
    try:
        info = await channel_service.configure_channel(payload.channel_id, reset_history=payload.reset_history)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Canal configurado com sucesso.", "channel": info}


@router.get("/channels/available")
async def list_available_channels(
    channel_service: ChannelService = Depends(get_channel_service),
) -> Dict[str, Any]:
    try:
        items = await channel_service.list_available_channels()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}
