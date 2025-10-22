import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...application.services.message_service import MessageQueryService
from ...core.container import ApplicationContainer
from ...services.message_stream import MessageStreamManager

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket) -> None:
    container: ApplicationContainer = getattr(websocket.app.state, "container", None)  # type: ignore[attr-defined]
    if not container:
        logger.error("Application container not initialised for websocket connection.")
        await websocket.close(code=1011)
        return

    manager: MessageStreamManager = container.stream_manager
    message_service: MessageQueryService = container.message_service

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
