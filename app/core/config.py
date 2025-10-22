import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Settings:
    """Centralised application configuration sourced from environment variables."""

    def __init__(self) -> None:
        load_dotenv()
        self.telegram_api_id = self._get_int("TELEGRAM_API_ID")
        self.telegram_api_hash = self._get("TELEGRAM_API_HASH")
        self.telegram_session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram_session")
        self.default_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        self.telegram_phone_number = os.getenv("TELEGRAM_PHONE")
        self.database_path = Path(os.getenv("DATABASE_PATH", "data/app.db")).resolve()
        self.initial_history_limit = self._get_int("TELEGRAM_INITIAL_HISTORY", default=200)
        origins = os.getenv("CORS_ALLOW_ORIGINS")
        if origins:
            self.cors_allow_origins = [item.strip() for item in origins.split(",") if item.strip()]
        else:
            self.cors_allow_origins = ["*"]

    @staticmethod
    def _get(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {key}")
        return value

    @staticmethod
    def _get_int(key: str, default: Optional[int] = None) -> int:
        value = os.getenv(key)
        if value is None:
            if default is None:
                raise RuntimeError(f"Missing required environment variable: {key}")
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise RuntimeError(f"Environment variable {key} must be an integer") from exc
