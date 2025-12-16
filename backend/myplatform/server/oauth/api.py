"""
OAuth API endpoints for MyPlatform.
Handles OAuth authorization flows for various connectors.
Ported from ee/esa/server/oauth/api.py
"""
import base64
import uuid

from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from myplatform.server.oauth.api_router import router
from esa.auth.users import current_admin_user
from esa.configs.app_configs import DEV_MODE
from esa.configs.constants import DocumentSource
from esa.db.models import User
from esa.redis.redis_pool import get_redis_client
from esa.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


@router.post("/prepare-authorization-request")
def prepare_authorization_request(
    connector: DocumentSource,
    redirect_on_success: str | None,
    user: User = Depends(current_admin_user),
    tenant_id: str | None = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    Used by the frontend to generate the URL for the user's browser during auth request.
    
    Example: https://www.oauth.com/oauth2-servers/authorization/the-authorization-request/
    
    Args:
        connector: The document source type (GOOGLE_DRIVE, SLACK, CONFLUENCE, etc.)
        redirect_on_success: URL to redirect after successful OAuth
        user: The current admin user
        tenant_id: The tenant ID
        
    Returns:
        JSON response with the OAuth URL
    """
    # Create random OAuth state param for security and to retrieve user data later
    oauth_uuid = uuid.uuid4()
    oauth_uuid_str = str(oauth_uuid)

    # URL-safe base64 encode the UUID for the OAuth URL
    oauth_state = (
        base64.urlsafe_b64encode(oauth_uuid.bytes).rstrip(b"=").decode("utf-8")
    )

    session: str | None = None
    oauth_url: str | None = None

    if connector == DocumentSource.SLACK:
        from myplatform.server.oauth.slack import SlackOAuth
        
        if not DEV_MODE:
            oauth_url = SlackOAuth.generate_oauth_url(oauth_state)
        else:
            oauth_url = SlackOAuth.generate_dev_oauth_url(oauth_state)
        session = SlackOAuth.session_dump_json(
            email=user.email, redirect_on_success=redirect_on_success
        )
    elif connector == DocumentSource.CONFLUENCE:
        from myplatform.server.oauth.confluence_cloud import ConfluenceCloudOAuth
        
        if not DEV_MODE:
            oauth_url = ConfluenceCloudOAuth.generate_oauth_url(oauth_state)
        else:
            oauth_url = ConfluenceCloudOAuth.generate_dev_oauth_url(oauth_state)
        session = ConfluenceCloudOAuth.session_dump_json(
            email=user.email, redirect_on_success=redirect_on_success
        )
    elif connector == DocumentSource.GOOGLE_DRIVE:
        from myplatform.server.oauth.google_drive import GoogleDriveOAuth
        
        if not DEV_MODE:
            oauth_url = GoogleDriveOAuth.generate_oauth_url(oauth_state)
        else:
            oauth_url = GoogleDriveOAuth.generate_dev_oauth_url(oauth_state)
        session = GoogleDriveOAuth.session_dump_json(
            email=user.email, redirect_on_success=redirect_on_success
        )

    if not oauth_url:
        raise HTTPException(
            status_code=404,
            detail=f"The document source type {connector} does not have OAuth implemented",
        )

    if not session:
        raise HTTPException(
            status_code=500,
            detail=f"The document source type {connector} failed to generate an OAuth session.",
        )

    r = get_redis_client(tenant_id=tenant_id)

    # Store important session state to retrieve when the user is redirected back
    # 10 min is the max we want an OAuth flow to be valid
    r.set(f"da_oauth:{oauth_uuid_str}", session, ex=600)

    return JSONResponse(content={"url": oauth_url})


@router.get("/callback")
def oauth_callback(
    state: str,
    code: str,
    tenant_id: str | None = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    Handle OAuth callback from external provider.
    
    Args:
        state: OAuth state parameter
        code: Authorization code from provider
        tenant_id: The tenant ID
        
    Returns:
        JSON response with redirect URL
    """
    try:
        # Decode the state to get the UUID
        padding = 4 - len(state) % 4
        if padding != 4:
            state += "=" * padding
        oauth_uuid_bytes = base64.urlsafe_b64decode(state)
        oauth_uuid = uuid.UUID(bytes=oauth_uuid_bytes)
        oauth_uuid_str = str(oauth_uuid)
    except Exception as e:
        logger.error(f"Invalid OAuth state: {e}")
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    r = get_redis_client(tenant_id=tenant_id)
    
    # Retrieve session from Redis
    session_data = r.get(f"da_oauth:{oauth_uuid_str}")
    if not session_data:
        raise HTTPException(
            status_code=400,
            detail="OAuth session expired or not found",
        )

    # Clean up Redis
    r.delete(f"da_oauth:{oauth_uuid_str}")

    # Process the OAuth callback (exchange code for tokens)
    # This would be implemented based on the specific provider
    
    return JSONResponse(content={"status": "success"})
