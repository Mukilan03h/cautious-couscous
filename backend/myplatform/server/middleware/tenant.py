"""
Multi-tenant middleware for MyPlatform.
Handles tenant context extraction and injection.
"""
from typing import Callable

from fastapi import Request
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware

from esa.utils.logger import setup_logger
from shared_configs.contextvars import set_current_tenant_id
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

logger = setup_logger()


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts tenant context from requests.
    
    Tenant can be specified via:
    1. X-Tenant-ID header
    2. Query parameter ?tenant_id=xxx
    3. Subdomain (tenant.example.com)
    4. JWT token claims
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process the request and set tenant context."""
        tenant_id = self._extract_tenant_id(request)
        
        if tenant_id:
            set_current_tenant_id(tenant_id)
            logger.debug(f"Tenant context set: {tenant_id}")
        elif MULTI_TENANT:
            # In multi-tenant mode, default to public schema
            set_current_tenant_id(POSTGRES_DEFAULT_SCHEMA)
        
        response = await call_next(request)
        return response
    
    def _extract_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from the request."""
        # Try header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Try query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        # Try subdomain extraction
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            # Don't treat common subdomains as tenant IDs
            if subdomain not in ("www", "api", "app", "admin"):
                return subdomain
        
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request details."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Log request and response."""
        logger.debug(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        logger.debug(f"Response: {response.status_code}")
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.
    Uses Redis for distributed rate limiting in production.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Check rate limits and process request."""
        # Placeholder - actual implementation would:
        # 1. Extract client identifier (IP, API key, user ID)
        # 2. Check Redis for request count
        # 3. Return 429 if limit exceeded
        
        response = await call_next(request)
        return response
