"""
Secrets management utilities for MyPlatform.
Provides secure handling of sensitive configuration values.
"""
import os
from functools import lru_cache
from typing import Any

from esa.utils.logger import setup_logger

logger = setup_logger()


@lru_cache(maxsize=32)
def get_secret(key: str, default: Any = None) -> str | None:
    """
    Get a secret value from environment variables.
    
    Args:
        key: The environment variable name
        default: Default value if not found
        
    Returns:
        The secret value or default
    """
    value = os.environ.get(key, default)
    if value is None:
        logger.warning(f"Secret {key} not found in environment")
    return value


def get_required_secret(key: str) -> str:
    """
    Get a required secret value from environment variables.
    
    Args:
        key: The environment variable name
        
    Returns:
        The secret value
        
    Raises:
        ValueError: If the secret is not found
    """
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Required secret {key} not found in environment")
    return value


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask a secret value for logging purposes.
    
    Args:
        value: The secret value to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked string like "****abcd"
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]
