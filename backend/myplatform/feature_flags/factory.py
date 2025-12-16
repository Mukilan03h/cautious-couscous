"""
Feature flags factory for MyPlatform.
Ported from ee/esa/feature_flags/factory.py
"""
from typing import Protocol


class FeatureFlagProvider(Protocol):
    """Protocol for feature flag providers."""
    
    def is_enabled(self, feature_key: str, user_id: str | None = None) -> bool:
        """Check if a feature flag is enabled."""
        ...
    
    def get_variant(self, feature_key: str, user_id: str | None = None) -> str | None:
        """Get the variant of a feature flag."""
        ...


def get_feature_flag_provider() -> FeatureFlagProvider | None:
    """
    Get the configured feature flag provider.
    
    Returns:
        FeatureFlagProvider instance or None if not configured
    """
    from myplatform.configs.app_configs import POSTHOG_API_KEY
    
    if POSTHOG_API_KEY and POSTHOG_API_KEY != "FooBar":
        from myplatform.feature_flags.posthog_provider import PosthogFeatureFlagProvider
        return PosthogFeatureFlagProvider()
    
    return None
