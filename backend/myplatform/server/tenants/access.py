"""
Tenant access control for MyPlatform.
Ported from ee/esa/server/tenants/access.py
"""
import jwt
import time
import os
from typing import Optional

from esa.utils.logger import setup_logger

logger = setup_logger()

# JWT configuration
DATA_PLANE_SECRET = os.environ.get("DATA_PLANE_SECRET", "default_secret")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour


def generate_data_plane_token(
    tenant_id: Optional[str] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    Generate a JWT token for data plane communication.
    
    Args:
        tenant_id: Optional tenant ID to include in token
        extra_claims: Optional additional claims
        
    Returns:
        JWT token string
    """
    now = int(time.time())
    
    payload = {
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
        "type": "data_plane",
    }
    
    if tenant_id:
        payload["tenant_id"] = tenant_id
    
    if extra_claims:
        payload.update(extra_claims)
    
    token = jwt.encode(payload, DATA_PLANE_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_data_plane_token(token: str) -> Optional[dict]:
    """
    Verify a data plane token and return the claims.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Token claims if valid, None otherwise
    """
    try:
        claims = jwt.decode(token, DATA_PLANE_SECRET, algorithms=[JWT_ALGORITHM])
        return claims
    except jwt.ExpiredSignatureError:
        logger.warning("Data plane token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid data plane token: {e}")
        return None


def check_tenant_access(user_id: str, tenant_id: str) -> bool:
    """
    Check if a user has access to a tenant.
    
    Args:
        user_id: The user ID
        tenant_id: The tenant ID
        
    Returns:
        True if user has access
    """
    # TODO: Implement actual tenant access check from database
    # For now, return True if user_id and tenant_id are set
    return bool(user_id and tenant_id)


def get_tenant_for_user(user_id: str) -> Optional[str]:
    """
    Get the tenant ID associated with a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        Tenant ID if found, None otherwise
    """
    # TODO: Implement actual lookup from database
    return None
