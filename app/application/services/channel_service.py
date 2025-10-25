import json
from typing import Any, Dict, List

from ...domain.ports.persistence import (
    MessageRepository,
    SettingsRepository,
    StrategySignalRepository,
)
from ...services.telegram import TelegramService


class ChannelService:
    """Application service encapsulating channel configuration flows."""

    def __init__(
        self,
        telegram_service: TelegramService,
        settings_repository: SettingsRepository,
        message_repository: MessageRepository,
        signal_repository: StrategySignalRepository,
    ) -> None:
        self._telegram = telegram_service
        self._settings = settings_repository
        self._messages = message_repository
        self._signals = signal_repository

    def current_configuration(self) -> Dict[str, Any]:
        channels = self._load_channels()
        channel_ids = [item["id"] for item in channels]
        channel_titles = [item.get("title") for item in channels]
        last_inputs = self._load_channel_inputs()
        legacy_channel_id = self._settings.get_setting("channel_id")
        legacy_channel_title = self._settings.get_setting("channel_title")
        legacy_input = self._settings.get_setting("channel_input")

        return {
            "channel_id": self._settings.get_setting("channel_id"),
            "channel_title": self._settings.get_setting("channel_title"),
            "last_input": self._settings.get_setting("channel_input"),
            "channel_ids": channel_ids or ([legacy_channel_id] if legacy_channel_id else []),
            "channel_titles": channel_titles or ([legacy_channel_title] if legacy_channel_title else []),
            "channels": channels
            or (
                [{"id": legacy_channel_id, "title": legacy_channel_title}]
                if legacy_channel_id and legacy_channel_title
                else []
            ),
            "last_inputs": last_inputs or ([legacy_input] if legacy_input else []),
            "status": self._telegram.get_status(),
            "capture_state": self._telegram.get_capture_state(),
        }

    async def configure_channels(self, identifiers: List[str], reset_history: bool) -> List[Dict[str, Any]]:
        clean_identifiers: List[str] = []
        for identifier in identifiers:
            if not identifier:
                continue
            normalized = identifier.strip()
            if normalized and normalized not in clean_identifiers:
                clean_identifiers.append(normalized)

        infos = await self._telegram.set_channels(clean_identifiers, reset_history=reset_history)
        channels_payload = [
            {"id": info["channel_id"], "title": info["title"]} for info in infos
        ]
        inputs_payload = clean_identifiers[:]

        self._settings.set_setting("channels", json.dumps(channels_payload, ensure_ascii=False))
        self._settings.set_setting("channel_inputs", json.dumps(inputs_payload, ensure_ascii=False))

        if infos:
            self._settings.set_setting("channel_id", infos[0]["channel_id"])
            self._settings.set_setting("channel_title", infos[0]["title"])
            self._settings.set_setting("channel_input", clean_identifiers[0])
        else:
            self._settings.set_setting("channel_id", "")
            self._settings.set_setting("channel_title", "")
            self._settings.set_setting("channel_input", "")

        return infos

    async def configure_channel(self, channel_identifier: str, reset_history: bool) -> Dict[str, Any]:
        infos = await self.configure_channels([channel_identifier], reset_history=reset_history)
        return infos[0]

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
        status = self._telegram.get_status()
        channel_ids = status.get("channel_ids") or []
        if not channel_ids:
            raise ValueError("Nenhum canal configurado.")
        for channel_id in channel_ids:
            canonical_id = str(channel_id)
            self._messages.clear_messages_for_channel(canonical_id)
            self._signals.clear_signals_for_channel(canonical_id)

    def _load_channels(self) -> List[Dict[str, Any]]:
        raw = self._settings.get_setting("channels")
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        filtered: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and "id" in item:
                filtered.append({"id": str(item["id"]), "title": item.get("title")})
        return filtered

    def _load_channel_inputs(self) -> List[str]:
        raw = self._settings.get_setting("channel_inputs")
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in data if isinstance(item, (str, int))]
