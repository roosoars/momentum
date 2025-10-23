from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from ..models import Strategy, StrategySignal, User


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


class StrategyRepository(Protocol):
    """Persistence functions related to strategy metadata."""

    def create_strategy(
        self,
        name: str,
        channel_identifier: str,
        channel_id: Optional[str],
        channel_title: Optional[str],
        channel_linked_at: Optional[str],
        is_active: bool,
    ) -> Strategy:
        ...

    def update_strategy(
        self,
        strategy_id: int,
        *,
        name: Optional[str] = None,
        channel_identifier: Optional[str] = None,
        channel_id: Optional[str] = None,
        channel_title: Optional[str] = None,
        channel_linked_at: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_paused: Optional[bool] = None,
    ) -> Strategy:
        ...

    def delete_strategy(self, strategy_id: int) -> None:
        ...

    def get_strategy(self, strategy_id: int) -> Optional[Strategy]:
        ...

    def get_strategies(self) -> List[Strategy]:
        ...

    def get_strategies_by_channel(self, channel_id: str) -> List[Strategy]:
        ...


class StrategySignalRepository(Protocol):
    """Persistence functions related to parsed strategy signals."""

    def record_signal(
        self,
        strategy_id: int,
        channel_id: str,
        telegram_message_id: int,
        raw_message: Optional[str],
        parsed_payload: Dict[str, Any],
        status: str,
        error: Optional[str],
        received_at: str,
        processed_at: str,
    ) -> StrategySignal:
        ...

    def get_signals_for_strategy(
        self,
        strategy_id: int,
        limit: int,
        newer_than: Optional[str] = None,
    ) -> List[StrategySignal]:
        ...

    def clear_signals_for_channel(self, channel_id: str) -> None:
        ...

    def purge_signals_older_than(self, iso_timestamp: str) -> int:
        ...


class UserRepository(Protocol):
    """Persistence functions related to admin user accounts."""

    def get_user_by_email(self, email: str) -> Optional[User]:
        ...

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        ...

    def create_user(self, email: str, password_hash: str) -> User:
        ...

    def update_user_password(self, user_id: int, password_hash: str) -> User:
        ...


class PersistenceGateway(
    SettingsRepository,
    MessageRepository,
    StrategyRepository,
    StrategySignalRepository,
    UserRepository,
    Protocol,
):
    """Composite gateway combining every persistence concern used by the app."""

    pass
