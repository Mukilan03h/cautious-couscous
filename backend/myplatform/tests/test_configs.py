"""
Tests for myplatform connectors and configs.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestAppConfigs:
    """Tests for application configurations."""
    
    def test_permission_sync_frequencies(self):
        """Verify permission sync frequency configs exist."""
        from myplatform.configs.app_configs import (
            DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY,
            CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY,
            GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY,
            SLACK_PERMISSION_DOC_SYNC_FREQUENCY,
        )
        
        assert DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY == 300  # 5 minutes
        assert CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY == 1800  # 30 minutes
        assert GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY == 300  # 5 minutes
        assert SLACK_PERMISSION_DOC_SYNC_FREQUENCY == 300  # 5 minutes
    
    def test_posthog_configs(self):
        """Verify PostHog configuration defaults."""
        from myplatform.configs.app_configs import POSTHOG_API_KEY, POSTHOG_HOST
        
        assert POSTHOG_API_KEY == "FooBar"  # Default placeholder
        assert POSTHOG_HOST == "https://us.i.posthog.com"


class TestPermSyncValid:
    """Tests for permission sync validation."""
    
    def test_perm_sync_valid_sources(self):
        """Verify sources that support permission sync."""
        from myplatform.connectors.perm_sync_valid import PERM_SYNC_VALID_SOURCES
        from esa.configs.constants import DocumentSource
        
        # Key sources should support permission sync
        assert DocumentSource.GOOGLE_DRIVE in PERM_SYNC_VALID_SOURCES
        assert DocumentSource.SLACK in PERM_SYNC_VALID_SOURCES
        assert DocumentSource.CONFLUENCE in PERM_SYNC_VALID_SOURCES
        assert DocumentSource.GITHUB in PERM_SYNC_VALID_SOURCES
    
    def test_is_perm_sync_valid_function(self):
        """Verify is_perm_sync_valid function."""
        from myplatform.connectors.perm_sync_valid import is_perm_sync_valid
        from esa.configs.constants import DocumentSource
        
        assert is_perm_sync_valid(DocumentSource.GOOGLE_DRIVE) is True
        assert is_perm_sync_valid(DocumentSource.SLACK) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
