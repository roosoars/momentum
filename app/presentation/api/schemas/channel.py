from pydantic import BaseModel


class ChannelConfig(BaseModel):
    channel_id: str
    reset_history: bool = True
