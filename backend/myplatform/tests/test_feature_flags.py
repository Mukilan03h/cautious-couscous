"""
Tests for myplatform feature flags module.
"""
import pytest
from unittest.mock import MagicMock, patch

from myplatform.feature_flags.factory import get_feature_flag_provider


class TestFeatureFlagFactory:
    """Tests for feature flag factory."""
    
    @patch('myplatform.feature_flags.factory.POSTHOG_API_KEY', None)
    def test_no_provider_when_no_api_key(self):
        """Should return None when no PostHog API key is configured."""
        provider = get_feature_flag_provider()
        assert provider is None
    
    @patch('myplatform.feature_flags.factory.POSTHOG_API_KEY', 'FooBar')
    def test_no_provider_for_default_api_key(self):
        """Should return None for the default FooBar API key."""
        provider = get_feature_flag_provider()
        assert provider is None
    
    @patch('myplatform.feature_flags.factory.POSTHOG_API_KEY', 'phc_real_key_here')
    def test_returns_provider_with_real_key(self):
        """Should return PostHog provider with a real API key."""
        with patch('myplatform.feature_flags.posthog_provider.posthog', MagicMock()):
            provider = get_feature_flag_provider()
            assert provider is not None


class TestPosthogProvider:
    """Tests for PostHog feature flag provider."""
    
    def test_feature_disabled_when_posthog_not_installed(self):
        """Features should be disabled when PostHog is not installed."""
        with patch.dict('sys.modules', {'posthog': None}):
            with patch('myplatform.configs.app_configs.POSTHOG_API_KEY', 'test_key'):
                from myplatform.feature_flags.posthog_provider import PosthogFeatureFlagProvider
                provider = PosthogFeatureFlagProvider()
                result = provider.is_enabled('test_feature')
                # Should return False when PostHog is not available
                assert result is False
    
    def test_captures_events(self):
        """capture() should not raise errors."""
        mock_posthog = MagicMock()
        
        with patch.dict('sys.modules', {'posthog': mock_posthog}):
            with patch('myplatform.configs.app_configs.POSTHOG_API_KEY', 'test_key'):
                from myplatform.feature_flags.posthog_provider import PosthogFeatureFlagProvider
                provider = PosthogFeatureFlagProvider()
                provider.capture('user123', 'test_event', {'key': 'value'})
                # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
