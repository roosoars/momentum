from typing import Dict, List, Optional

from ...domain.ports.persistence import MessageRepository


class MessageQueryService:
    """Read-only access to stored Telegram messages."""

    def __init__(self, message_repository: MessageRepository) -> None:
        self._messages = message_repository

    def get_recent_messages(
        self, limit: int, channel_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, object]]]:
        items = self._messages.get_recent_messages(channel_id=channel_id, limit=limit)
        return {"items": items, "count": len(items)}
