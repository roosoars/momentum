from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .container import ApplicationContainer
from .logging import configure_logging
from ..application.services.auth_service import AuthService
from ..application.services.channel_service import ChannelService
from ..application.services.message_service import MessageQueryService
from ..infrastructure.persistence.sqlite import SQLitePersistence
from ..presentation.api.routers import auth as auth_router
from ..presentation.api.routers import config as config_router
from ..presentation.api.routers import messages as messages_router
from ..presentation.websocket import routes as websocket_routes
from ..services.message_stream import MessageStreamManager
from ..services.telegram import TelegramService

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

    app.include_router(auth_router.router)
    app.include_router(config_router.router)
    app.include_router(messages_router.router)
    app.include_router(websocket_routes.router)

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
        stream_manager = MessageStreamManager()
        auth_service = AuthService(telegram, persistence)
        channel_service = ChannelService(telegram, persistence)
        message_service = MessageQueryService(persistence)

        container = ApplicationContainer(
            settings=settings,
            persistence=persistence,
            telegram_service=telegram,
            stream_manager=stream_manager,
            auth_service=auth_service,
            channel_service=channel_service,
            message_service=message_service,
        )

        app.state.container = container  # type: ignore[attr-defined]

        await telegram.start()
        telegram.add_listener(stream_manager.broadcast_new_message)

        if telegram.is_authorized:
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
            telegram.remove_listener(stream_manager.broadcast_new_message)
            await telegram.stop()
            persistence.close()

    return lifespan
