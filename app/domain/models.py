from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class Strategy:
    id: int
    name: str
    channel_identifier: str
    channel_id: Optional[str]
    channel_title: Optional[str]
    channel_linked_at: Optional[datetime]
    is_active: bool
    is_paused: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class StrategySignal:
    id: int
    strategy_id: int
    channel_id: str
    telegram_message_id: int
    raw_message: Optional[str]
    parsed_payload: Dict[str, Any]
    status: str
    error: Optional[str]
    received_at: datetime
    processed_at: datetime


@dataclass(slots=True)
class User:
    id: int
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
