from dataclasses import dataclass

from ..application.services.admin_auth_service import AdminAuthService
from ..application.services.auth_service import AuthService
from ..application.services.channel_service import ChannelService
from ..application.services.strategy_service import StrategyService
from .config import Settings
from ..domain.ports.persistence import PersistenceGateway
from ..services.api_key_service import ApiKeyService
from ..services.email_service import EmailService
from ..services.openai_parser import SignalParser
from ..services.signal_processor import SignalProcessor
from ..services.stripe_service import StripeService
from ..services.subscription_service import SubscriptionService
from ..services.telegram import TelegramService
from ..services.user_service import UserService


@dataclass(slots=True)
class ApplicationContainer:
    """Dependency registry shared across the FastAPI application lifecycle."""

    settings: Settings
    persistence: PersistenceGateway
    telegram_service: TelegramService
    signal_parser: SignalParser
    signal_processor: SignalProcessor
    strategy_service: StrategyService
    admin_auth_service: AdminAuthService
    auth_service: AuthService
    channel_service: ChannelService
    stripe_service: StripeService
    user_service: UserService
    subscription_service: SubscriptionService
    api_key_service: ApiKeyService
    email_service: EmailService
