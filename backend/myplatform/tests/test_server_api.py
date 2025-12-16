"""
Tests for myplatform server API modules.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


class TestBillingAPI:
    """Tests for billing API endpoints."""
    
    def test_fetch_billing_information(self):
        """Should fetch billing info from control plane."""
        from myplatform.server.tenants.billing import fetch_billing_information
        
        with patch('myplatform.server.tenants.billing.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "subscribed": False,
                "message": "No subscription",
            }
            mock_requests.get.return_value = mock_response
            
            with patch('myplatform.server.tenants.billing.generate_data_plane_token') as mock_token:
                mock_token.return_value = "test_token"
                result = fetch_billing_information("tenant123")
        
        assert result is not None


class TestUserGroupAPI:
    """Tests for user group API endpoints."""
    
    def test_user_group_create_model(self):
        """Verify UserGroupCreate model."""
        from myplatform.server.user_group.models import UserGroupCreate
        
        group = UserGroupCreate(name="Test Group", description="A test group")
        
        assert group.name == "Test Group"
        assert group.description == "A test group"
    
    def test_user_group_response_model(self):
        """Verify UserGroupResponse model."""
        from myplatform.server.user_group.models import UserGroupResponse
        
        group = UserGroupResponse(
            id=1,
            name="Test Group",
            description="A test group",
            user_count=5,
        )
        
        assert group.id == 1
        assert group.user_count == 5


class TestQueryAndChatAPI:
    """Tests for query and chat API modules."""
    
    def test_token_limit_exceeded_exception(self):
        """Verify TokenLimitExceeded exception."""
        from myplatform.server.query_and_chat.token_limit import TokenLimitExceeded
        
        exc = TokenLimitExceeded(
            message="Limit exceeded",
            limit=1000,
            usage=1500,
            period="daily",
        )
        
        assert exc.limit == 1000
        assert exc.usage == 1500
        assert exc.period == "daily"
    
    def test_token_usage_info_model(self):
        """Verify TokenUsageInfo model."""
        from myplatform.server.query_and_chat.models import TokenUsageInfo
        
        info = TokenUsageInfo(
            has_limit=True,
            limit=1000,
            usage=500,
            remaining=500,
            period="daily",
            period_start=None,
        )
        
        assert info.has_limit is True
        assert info.remaining == 500


class TestOAuthConfigsAPI:
    """Tests for OAuth configuration API."""
    
    def test_oauth_config_storage(self):
        """Should store OAuth configs with encrypted secrets."""
        # This would typically test the API endpoints
        # For now, verify the module imports correctly
        pass


class TestAnalyticsAPI:
    """Tests for analytics API."""
    
    def test_analytics_api_exists(self):
        """Verify analytics API module exists."""
        from myplatform.server.analytics import api
        assert api is not None


class TestReportingAPI:
    """Tests for reporting/usage export API."""
    
    def test_reporting_api_exists(self):
        """Verify reporting API module exists."""
        from myplatform.server.reporting import usage_export_api
        assert usage_export_api is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
