"""
PostHog feature flag provider for MyPlatform.
Ported from ee/esa/feature_flags/posthog_provider.py
"""
from myplatform.configs.app_configs import POSTHOG_API_KEY, POSTHOG_HOST
from esa.utils.logger import setup_logger

logger = setup_logger()


class PosthogFeatureFlagProvider:
    """Feature flag provider using PostHog."""
    
    def __init__(self):
        try:
            import posthog
            posthog.project_api_key = POSTHOG_API_KEY
            posthog.host = POSTHOG_HOST
            self._posthog = posthog
            logger.info("PostHog feature flag provider initialized")
        except ImportError:
            logger.warning("PostHog not installed, feature flags will not work")
            self._posthog = None
    
    def is_enabled(self, feature_key: str, user_id: str | None = None) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            feature_key: The feature flag key
            user_id: Optional user ID for user-specific flags
            
        Returns:
            True if the feature is enabled
        """
        if not self._posthog:
            return False
        
        try:
            distinct_id = user_id or "anonymous"
            return self._posthog.feature_enabled(feature_key, distinct_id)
        except Exception as e:
            logger.warning(f"Error checking feature flag {feature_key}: {e}")
            return False
    
    def get_variant(self, feature_key: str, user_id: str | None = None) -> str | None:
        """
        Get the variant of a feature flag.
        
        Args:
            feature_key: The feature flag key
            user_id: Optional user ID for user-specific variants
            
        Returns:
            The variant string or None
        """
        if not self._posthog:
            return None
        
        try:
            distinct_id = user_id or "anonymous"
            return self._posthog.get_feature_flag(feature_key, distinct_id)
        except Exception as e:
            logger.warning(f"Error getting feature flag variant {feature_key}: {e}")
            return None
    
    def capture(self, user_id: str, event: str, properties: dict | None = None) -> None:
        """
        Capture an event in PostHog.
        
        Args:
            user_id: The user ID
            event: The event name
            properties: Optional event properties
        """
        if not self._posthog:
            return
        
        try:
            self._posthog.capture(user_id, event, properties or {})
        except Exception as e:
            logger.warning(f"Error capturing PostHog event {event}: {e}")
    
    def identify(self, user_id: str, properties: dict | None = None) -> None:
        """
        Identify a user in PostHog.
        
        Args:
            user_id: The user ID
            properties: Optional user properties
        """
        if not self._posthog:
            return
        
        try:
            self._posthog.identify(user_id, properties or {})
        except Exception as e:
            logger.warning(f"Error identifying user in PostHog: {e}")
