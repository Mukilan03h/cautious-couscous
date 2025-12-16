"""
Main entry point for MyPlatform backend.
Integrates all routers and middleware.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from myplatform.server.middleware.tenant import TenantMiddleware
from myplatform.server.middleware.tenant import RequestLoggingMiddleware
from esa.utils.logger import setup_logger

logger = setup_logger()


def create_myplatform_app() -> FastAPI:
    """
    Create and configure the MyPlatform FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="MyPlatform API",
        description="Enterprise Knowledge Platform API",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TenantMiddleware)
    
    # Register routers
    _register_routers(app)
    
    logger.info("MyPlatform application initialized")
    return app


def _register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    # OAuth router
    from myplatform.server.oauth.api import router as oauth_router
    app.include_router(oauth_router, tags=["OAuth"])
    
    # OAuth configs router (for managing OAuth client credentials)
    try:
        from myplatform.server.oauth.configs_api import router as oauth_configs_router
        app.include_router(oauth_configs_router, tags=["OAuth Configs"])
    except ImportError:
        logger.debug("OAuth configs router not available")
    
    # Billing router
    try:
        from myplatform.server.billing.api import router as billing_router
        app.include_router(billing_router, tags=["Billing"])
    except ImportError:
        logger.debug("Billing router not available")
    
    # Enterprise settings routers
    from myplatform.server.enterprise_settings.api import admin_router as enterprise_admin_router
    from myplatform.server.enterprise_settings.api import basic_router as enterprise_basic_router
    app.include_router(enterprise_admin_router, tags=["Enterprise Settings"])
    app.include_router(enterprise_basic_router, tags=["Enterprise Settings"])
    
    # Reporting router
    from myplatform.server.reporting.usage_export_api import router as reporting_router
    app.include_router(reporting_router, tags=["Reporting"])
    
    # Analytics router
    try:
        from myplatform.server.analytics.api import router as analytics_router
        app.include_router(analytics_router, tags=["Analytics"])
    except ImportError:
        logger.debug("Analytics router not available")
    
    # RBAC router
    try:
        from myplatform.server.rbac.api import router as rbac_router
        app.include_router(rbac_router, tags=["RBAC"])
    except ImportError:
        logger.debug("RBAC router not available")
    
    # Query history router
    try:
        from myplatform.server.query_history.api import router as query_history_router
        app.include_router(query_history_router, tags=["Query History"])
    except ImportError:
        logger.debug("Query history router not available")
    
    # Permissions router
    try:
        from myplatform.server.permissions.api import router as permissions_router
        app.include_router(permissions_router, tags=["Permissions"])
    except ImportError:
        logger.debug("Permissions router not available")
    
    # Connector sync router
    try:
        from myplatform.server.connector_sync.api import router as connector_sync_router
        app.include_router(connector_sync_router, tags=["Connector Sync"])
    except ImportError:
        logger.debug("Connector sync router not available")
    
    logger.info("All routers registered")


# Health check endpoint
def add_health_check(app: FastAPI) -> None:
    """Add health check endpoint to the app."""
    
    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "myplatform"}
    
    @app.get("/")
    def root():
        return {"message": "MyPlatform API", "version": "1.0.0"}


# Create the application instance
app = create_myplatform_app()
add_health_check(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
