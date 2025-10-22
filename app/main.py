"""FastAPI ASGI application entrypoint."""

from .core.app_factory import create_application

app = create_application()

__all__ = ("app",)
