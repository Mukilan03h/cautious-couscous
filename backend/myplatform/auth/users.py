"""
User authentication utilities for MyPlatform.
Provides authentication helpers, superuser validation, and JWT handling.
Ported from ee/esa/auth/users.py
"""
from datetime import datetime
from typing import Any

import jwt
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from esa.auth.users import current_admin_user
from esa.configs.app_configs import AUTH_TYPE
from esa.configs.app_configs import USER_AUTH_SECRET
from esa.db.models import User
from esa.utils.logger import setup_logger


logger = setup_logger()

# Configuration for super users (can be set via environment)
SUPER_USERS: list[str] = []
SUPER_CLOUD_API_KEY: str | None = None


def verify_auth_setting() -> None:
    """
    Verify that authentication is properly configured.
    All auth flows are valid for the custom platform.
    """
    logger.notice(f"Using Auth Type: {AUTH_TYPE.value}")


def get_default_admin_user_emails_() -> list[str]:
    """
    Get the list of default admin user emails from seed config.
    
    Returns:
        List of admin email addresses
    """
    from myplatform.server.seeding import get_seed_config
    
    seed_config = get_seed_config()
    if seed_config and seed_config.admin_user_emails:
        return seed_config.admin_user_emails
    return []


async def current_cloud_superuser(
    request: Request,
    user: User | None = Depends(current_admin_user),
) -> User | None:
    """
    Dependency to verify the current user is a cloud superuser.
    
    Args:
        request: The FastAPI request object
        user: The current admin user (from dependency)
        
    Returns:
        The verified superuser
        
    Raises:
        HTTPException: If authentication fails or user is not a superuser
    """
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if api_key != SUPER_CLOUD_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if user and user.email not in SUPER_USERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User must be a cloud superuser to perform this action.",
        )
    return user


def generate_anonymous_user_jwt_token(tenant_id: str) -> str:
    """
    Generate a JWT token for anonymous user access.
    
    Args:
        tenant_id: The tenant ID for the anonymous user
        
    Returns:
        JWT token string
    """
    payload = {
        "tenant_id": tenant_id,
        "iat": datetime.utcnow(),  # Issued at time
        "type": "anonymous",
    }

    return jwt.encode(payload, USER_AUTH_SECRET, algorithm="HS256")


def decode_anonymous_user_jwt_token(token: str) -> dict[str, Any]:
    """
    Decode an anonymous user JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If the token is invalid
    """
    return jwt.decode(token, USER_AUTH_SECRET, algorithms=["HS256"])


def generate_api_key_token(
    user_id: str,
    tenant_id: str,
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
) -> str:
    """
    Generate an API key token for programmatic access.
    
    Args:
        user_id: The user ID the token is for
        tenant_id: The tenant ID
        scopes: Optional list of permission scopes
        expires_in_days: Optional expiration in days
        
    Returns:
        API key token string
    """
    from datetime import timedelta
    
    payload: dict[str, Any] = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "iat": datetime.utcnow(),
        "type": "api_key",
    }
    
    if scopes:
        payload["scopes"] = scopes
    
    if expires_in_days:
        payload["exp"] = datetime.utcnow() + timedelta(days=expires_in_days)

    return jwt.encode(payload, USER_AUTH_SECRET, algorithm="HS256")


def validate_api_key_token(token: str) -> dict[str, Any]:
    """
    Validate and decode an API key token.
    
    Args:
        token: The API key token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If the token is invalid or expired
    """
    return jwt.decode(token, USER_AUTH_SECRET, algorithms=["HS256"])


def is_user_admin(user: User | None) -> bool:
    """
    Check if a user has admin privileges.
    
    Args:
        user: The user to check
        
    Returns:
        True if the user is an admin
    """
    if user is None:
        return False
    
    from esa.db.models import UserRole
    return user.role == UserRole.ADMIN


def is_user_curator(user: User | None) -> bool:
    """
    Check if a user has curator privileges.
    
    Args:
        user: The user to check
        
    Returns:
        True if the user is a curator
    """
    if user is None:
        return False
    
    from esa.db.models import UserRole
    return user.role in (UserRole.ADMIN, UserRole.CURATOR, UserRole.GLOBAL_CURATOR)
