"""Desenvolvimento local: SQLite, debug toolbar opcional, sem HTTPS."""

from .base import *  # noqa: F403

DEBUG = True

# Debug toolbar apenas se instalado (grupo dev)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]  # noqa: F405
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass
