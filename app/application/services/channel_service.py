from typing import Any, Dict

from ...domain.ports.persistence import SettingsRepository
from ...services.telegram import TelegramService


class ChannelService:
    """Application service encapsulating channel configuration flows."""

    def __init__(self, telegram_service: TelegramService, settings_repository: SettingsRepository) -> None:
        self._telegram = telegram_service
        self._settings = settings_repository

    def current_configuration(self) -> Dict[str, Any]:
        return {
            "channel_id": self._settings.get_setting("channel_id"),
            "channel_title": self._settings.get_setting("channel_title"),
            "last_input": self._settings.get_setting("channel_input"),
            "status": self._telegram.get_status(),
        }

    async def configure_channel(self, channel_identifier: str, reset_history: bool) -> Dict[str, Any]:
        info = await self._telegram.set_channel(channel_identifier, reset_history=reset_history)
        self._settings.set_setting("channel_id", info["channel_id"])
        self._settings.set_setting("channel_title", info["title"])
        self._settings.set_setting("channel_input", channel_identifier)
        return info
