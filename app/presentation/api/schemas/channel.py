from typing import List, Optional

from pydantic import BaseModel, Field, root_validator


class ChannelConfig(BaseModel):
    channels: List[str] = Field(..., min_items=1, max_items=5)
    reset_history: bool = True
    channel_id: Optional[str] = None  # compat

    @root_validator(pre=True)
    def ensure_channels(cls, values: dict) -> dict:
        if "channels" not in values or not values.get("channels"):
            legacy = values.get("channel_id")
            if legacy:
                values["channels"] = [legacy]
        if "channels" in values and isinstance(values["channels"], list):
            deduped = []
            for item in values["channels"]:
                if isinstance(item, str):
                    normalized = item.strip()
                    if normalized and normalized not in deduped:
                        deduped.append(normalized)
            values["channels"] = deduped
        return values
