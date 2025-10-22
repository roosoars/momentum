from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StrategyCreatePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    channel_identifier: str = Field(..., min_length=1, max_length=120)
    activate: bool = Field(default=False)


class StrategyRenamePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class StrategyAssignChannelPayload(BaseModel):
    channel_identifier: str = Field(..., min_length=1, max_length=120)


class StrategySignalQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    newer_than: Optional[str] = None
