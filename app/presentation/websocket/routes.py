import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ...application.services.message_service import MessageQueryService
from ...core.dependencies import get_message_service, get_stream_manager
from ...services.message_stream import MessageStreamManager

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/ws/messages")
async def websocket_messages(
    websocket: WebSocket,
    manager: MessageStreamManager = Depends(get_stream_manager),
    message_service: MessageQueryService = Depends(get_message_service),
) -> None:
    await manager.connect(websocket)
    try:
        history_payload = message_service.get_recent_messages(limit=50)
        await manager.send_history(websocket, history_payload["items"])
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
        logger.exception("Unexpected WebSocket error")
