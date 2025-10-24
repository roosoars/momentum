from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .container import ApplicationContainer
from .logging import configure_logging
from ..application.services.admin_auth_service import AdminAuthService
from ..application.services.auth_service import AuthService
from ..application.services.channel_service import ChannelService
from ..application.services.strategy_service import StrategyService
from ..infrastructure.persistence.sqlite import SQLitePersistence
from ..infrastructure.repositories.api_key_repository import ApiKeyRepository
from ..infrastructure.repositories.subscription_repository import SubscriptionRepository
from ..infrastructure.repositories.user_repository import UserRepository
from ..presentation.api.routers import admin as admin_router
from ..presentation.api.routers import auth as auth_router
from ..presentation.api.routers import config as config_router
from ..presentation.api.routers import strategies as strategies_router
from ..presentation.api.routers import stripe_router
from ..presentation.api.routers import user_router
from ..services.api_key_service import ApiKeyService
from ..services.email_service import EmailService
from ..services.openai_parser import SignalParser
from ..services.signal_processor import SignalProcessor
from ..services.stripe_service import StripeService
from ..services.subscription_service import SubscriptionService
from ..services.telegram import TelegramService
from ..services.user_service import UserService

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    settings = Settings()

    app = FastAPI(title="Telegram Channel Collector", lifespan=_create_lifespan(settings))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin_router.router)
    app.include_router(auth_router.router)
    app.include_router(config_router.router)
    app.include_router(strategies_router.router)
    app.include_router(stripe_router.router)
    app.include_router(user_router.router)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        container: ApplicationContainer = app.state.container  # type: ignore[attr-defined]
        return {"ok": True, "telegram": container.telegram_service.get_status()}

    return app


def _create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        persistence = SQLitePersistence(settings.database_path)
        telegram = TelegramService(
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            session_name=settings.telegram_session_name,
            message_repository=persistence,
            history_limit=settings.initial_history_limit,
        )
        signal_parser = SignalParser(settings.openai_api_key, settings.openai_model)
        signal_processor = SignalProcessor(
            persistence,
            signal_parser,
            retention_hours=settings.signal_retention_hours,
            max_workers=settings.signal_worker_count,
        )
        strategy_service = StrategyService(persistence, telegram, signal_processor)
        admin_auth_service = AdminAuthService(
            persistence=persistence,
            secret_key=settings.admin_token_secret,
            token_exp_minutes=settings.admin_token_exp_minutes,
        )
        admin_auth_service.ensure_default_admin(
            settings.admin_default_email, settings.admin_default_password
        )
        auth_service = AuthService(telegram, persistence)
        channel_service = ChannelService(
            telegram,
            persistence,
            persistence,
            persistence,
        )
        stripe_service = StripeService(persistence)

        # User system services
        user_repository = UserRepository(settings.database_path)
        subscription_repository = SubscriptionRepository(settings.database_path)
        api_key_repository = ApiKeyRepository(settings.database_path)

        user_service = UserService(
            user_repository=user_repository,
            jwt_secret=settings.admin_token_secret,  # Using same secret for now
        )
        subscription_service = SubscriptionService(
            subscription_repository=subscription_repository,
        )
        api_key_service = ApiKeyService(api_key_repository=api_key_repository)
        email_service = EmailService()

        container = ApplicationContainer(
            settings=settings,
            persistence=persistence,
            telegram_service=telegram,
            signal_parser=signal_parser,
            signal_processor=signal_processor,
            strategy_service=strategy_service,
            admin_auth_service=admin_auth_service,
            auth_service=auth_service,
            channel_service=channel_service,
            stripe_service=stripe_service,
            user_service=user_service,
            subscription_service=subscription_service,
            api_key_service=api_key_service,
            email_service=email_service,
        )

        app.state.container = container  # type: ignore[attr-defined]

        await signal_processor.start()
        await telegram.start()
        telegram.add_listener(strategy_service.handle_incoming_message)

        await strategy_service.initialize()

        existing_strategies = await strategy_service.list_strategies()
        if telegram.is_authorized and not existing_strategies:
            stored_channel = persistence.get_setting("channel_id")
            startup_channel = stored_channel or settings.default_channel_id
            if startup_channel:
                try:
                    info = await telegram.set_channel(startup_channel, reset_history=False)
                    persistence.set_setting("channel_id", info["channel_id"])
                    persistence.set_setting("channel_title", info["title"])
                    persistence.set_setting("channel_input", startup_channel)
                except ValueError as exc:  # pragma: no cover - defensive startup
                    logger.warning("Unable to configure initial channel %s: %s", startup_channel, exc)

        try:
            yield
        finally:
            telegram.remove_listener(strategy_service.handle_incoming_message)
            await signal_processor.stop()
            await telegram.stop()
            persistence.close()

    return lifespan
