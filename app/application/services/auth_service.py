from typing import Any, Dict

from ...domain.ports.persistence import SettingsRepository
from ...services.telegram import TelegramService


class AuthService:
    """Coordinates authentication flows with Telegram."""

    def __init__(self, telegram_service: TelegramService, settings_repository: SettingsRepository) -> None:
        self._telegram = telegram_service
        self._settings = settings_repository

    def status(self) -> Dict[str, Any]:
        return self._telegram.get_status()

    async def send_login_code(self, phone: str) -> Dict[str, Any]:
        result = await self._telegram.send_login_code(phone)
        self._settings.set_setting("telegram_phone", phone.strip())
        return result

    async def verify_login_code(self, code: str) -> Dict[str, Any]:
        return await self._telegram.verify_login_code(code)

    async def provide_password(self, password: str) -> Dict[str, Any]:
        return await self._telegram.provide_password(password)

    async def log_out(self) -> None:
        await self._telegram.log_out()
        self._settings.set_setting("channel_id", "")
        self._settings.set_setting("channel_title", "")
        self._settings.set_setting("channel_input", "")
        self._settings.set_setting("channels", "[]")
        self._settings.set_setting("channel_inputs", "[]")
