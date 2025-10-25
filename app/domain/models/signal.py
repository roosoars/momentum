from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


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
