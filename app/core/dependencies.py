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


def get_telegram_service(container: ApplicationContainer = Depends(get_container)):
    return container.telegram_service


def get_persistence_gateway(container: ApplicationContainer = Depends(get_container)):
    return container.persistence


def get_strategy_service(container: ApplicationContainer = Depends(get_container)):
    return container.strategy_service


def get_signal_processor(container: ApplicationContainer = Depends(get_container)):
    return container.signal_processor


def get_signal_parser(container: ApplicationContainer = Depends(get_container)):
    return container.signal_parser


def get_admin_auth_service(container: ApplicationContainer = Depends(get_container)):
    return container.admin_auth_service


def get_stripe_service(container: ApplicationContainer = Depends(get_container)):
    return container.stripe_service


def get_user_service(container: ApplicationContainer = Depends(get_container)):
    return container.user_service


def get_subscription_service(container: ApplicationContainer = Depends(get_container)):
    return container.subscription_service


def get_api_key_service(container: ApplicationContainer = Depends(get_container)):
    return container.api_key_service


def get_email_service(container: ApplicationContainer = Depends(get_container)):
    return container.email_service
