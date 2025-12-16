"""OAuth configuration feature module."""

from esa.server.features.oauth_config.api import admin_router
from esa.server.features.oauth_config.api import router

__all__ = ["admin_router", "router"]
