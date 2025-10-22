from typing import Any, Dict, List

from ...domain.ports.persistence import MessageRepository, SettingsRepository
from ...services.telegram import TelegramService
from ...services.message_stream import MessageStreamManager


class ChannelService:
    """Application service encapsulating channel configuration flows."""

    def __init__(
        self,
        telegram_service: TelegramService,
        settings_repository: SettingsRepository,
        message_repository: MessageRepository,
        stream_manager: MessageStreamManager,
    ) -> None:
        self._telegram = telegram_service
        self._settings = settings_repository
        self._messages = message_repository
        self._stream_manager = stream_manager

    def current_configuration(self) -> Dict[str, Any]:
        return {
            "channel_id": self._settings.get_setting("channel_id"),
            "channel_title": self._settings.get_setting("channel_title"),
            "last_input": self._settings.get_setting("channel_input"),
            "status": self._telegram.get_status(),
            "capture_state": self._telegram.get_capture_state(),
        }

    async def configure_channel(self, channel_identifier: str, reset_history: bool) -> Dict[str, Any]:
        info = await self._telegram.set_channel(channel_identifier, reset_history=reset_history)
        self._settings.set_setting("channel_id", info["channel_id"])
        self._settings.set_setting("channel_title", info["title"])
        self._settings.set_setting("channel_input", channel_identifier)
        return info

    async def list_available_channels(self) -> List[Dict[str, Any]]:
        return await self._telegram.list_available_channels()

    def capture_state(self) -> Dict[str, bool]:
        return self._telegram.get_capture_state()

    def pause_capture(self) -> Dict[str, bool]:
        return self._telegram.pause_capture()

    def resume_capture(self) -> Dict[str, bool]:
        return self._telegram.resume_capture()

    async def stop_capture(self) -> Dict[str, bool]:
        return await self._telegram.stop_capture()

    async def start_capture(self) -> Dict[str, bool]:
        return await self._telegram.start_capture()

    async def clear_history(self) -> None:
        channel_id = self._telegram.get_status().get("channel_id")
        if not channel_id:
            raise ValueError("Nenhum canal configurado.")
        self._messages.clear_messages_for_channel(channel_id)
        await self._stream_manager.broadcast_history([])
