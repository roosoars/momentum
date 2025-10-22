from dataclasses import dataclass

from ..application.services.auth_service import AuthService
from ..application.services.channel_service import ChannelService
from ..application.services.message_service import MessageQueryService
from .config import Settings
from ..domain.ports.persistence import PersistenceGateway
from ..services.message_stream import MessageStreamManager
from ..services.telegram import TelegramService


@dataclass(slots=True)
class ApplicationContainer:
    """Dependency registry shared across the FastAPI application lifecycle."""

    settings: Settings
    persistence: PersistenceGateway
    telegram_service: TelegramService
    stream_manager: MessageStreamManager
    auth_service: AuthService
    channel_service: ChannelService
    message_service: MessageQueryService
