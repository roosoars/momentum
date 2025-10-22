from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class SettingsRepository(Protocol):
    """Abstract storage for application key-value settings."""

    def get_setting(self, key: str) -> Optional[str]:
        ...

    def set_setting(self, key: str, value: str) -> None:
        ...


class MessageRepository(Protocol):
    """Abstract storage for Telegram message records."""

    def save_message(
        self,
        telegram_id: int,
        channel_id: str,
        sender: Optional[str],
        message: Optional[str],
        payload: Dict[str, Any],
        created_at: str,
    ) -> None:
        ...

    def clear_messages_for_channel(self, channel_id: str) -> None:
        ...

    def get_recent_messages(self, channel_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        ...


class PersistenceGateway(SettingsRepository, MessageRepository, Protocol):
    """Composite port combining the persistence capabilities used by the app."""

    pass
