from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
