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
    return {
        "message": "Canal configurado com sucesso.",
        "channel": info,
        "capture_state": channel_service.capture_state(),
    }


@router.get("/channels/available")
async def list_available_channels(
    channel_service: ChannelService = Depends(get_channel_service),
) -> Dict[str, Any]:
    try:
        items = await channel_service.list_available_channels()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}


@router.post("/capture/pause")
async def capture_pause(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    try:
        state = channel_service.pause_capture()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Captura pausada.", "capture_state": state}


@router.post("/capture/resume")
async def capture_resume(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    try:
        state = channel_service.resume_capture()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Captura retomada.", "capture_state": state}


@router.post("/capture/stop")
async def capture_stop(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    try:
        state = await channel_service.stop_capture()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Captura interrompida.", "capture_state": state}


@router.post("/capture/start")
async def capture_start(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    try:
        state = await channel_service.start_capture()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Captura iniciada.", "capture_state": state}


@router.post("/capture/clear-history")
async def capture_clear_history(channel_service: ChannelService = Depends(get_channel_service)) -> Dict[str, Any]:
    try:
        await channel_service.clear_history()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Histórico limpo."}
