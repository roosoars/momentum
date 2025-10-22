import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from ..domain.models import StrategySignal

logger = logging.getLogger(__name__)


class MessageStreamManager:
    """Manages WebSocket connections and broadcasts new messages."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.debug("WebSocket connected. Total: %s", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.debug("WebSocket disconnected. Total: %s", len(self._connections))

    async def broadcast_new_message(self, message: Dict) -> None:
        payload = {"type": "message", "data": jsonable_encoder(message)}
        await self._broadcast(payload)

    async def broadcast_signal(self, signal: StrategySignal) -> None:
        payload = {
            "type": "signal",
            "data": jsonable_encoder(
                {
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
            ),
        }
        await self._broadcast(payload)

    async def send_history(self, websocket: WebSocket, messages: List[Dict]) -> None:
        payload = {"type": "history", "data": jsonable_encoder(messages)}
        await websocket.send_json(payload)

    async def _broadcast(self, payload: Dict) -> None:
        async with self._lock:
            connections = list(self._connections)

        remove: List[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Failed to send WebSocket message; removing connection.")
                remove.append(websocket)

        if remove:
            async with self._lock:
                for websocket in remove:
                    if websocket in self._connections:
                        self._connections.remove(websocket)

    async def broadcast_history(self, messages: List[Dict]) -> None:
        payload = {"type": "history", "data": jsonable_encoder(messages)}
        await self._broadcast(payload)
