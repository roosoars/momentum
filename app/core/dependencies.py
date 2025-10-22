from fastapi import Depends, Request

from .container import ApplicationContainer


def get_container(request: Request) -> ApplicationContainer:
    container = getattr(request.app.state, "container", None)
    if not container:
        raise RuntimeError("Application container not initialised.")
    return container


def get_settings(container: ApplicationContainer = Depends(get_container)):
    return container.settings


def get_auth_service(container: ApplicationContainer = Depends(get_container)):
    return container.auth_service


def get_channel_service(container: ApplicationContainer = Depends(get_container)):
    return container.channel_service


def get_message_service(container: ApplicationContainer = Depends(get_container)):
    return container.message_service


def get_stream_manager(container: ApplicationContainer = Depends(get_container)):
    return container.stream_manager


def get_telegram_service(container: ApplicationContainer = Depends(get_container)):
    return container.telegram_service


def get_persistence_gateway(container: ApplicationContainer = Depends(get_container)):
    return container.persistence
