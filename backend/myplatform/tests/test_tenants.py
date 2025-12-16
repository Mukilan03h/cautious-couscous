"""
Tests for myplatform tenants module.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestProductGating:
    """Tests for product gating - all features should be enabled."""
    
    def test_no_features_are_gated(self):
        """All features should be enabled for free platform."""
        from myplatform.server.tenants.product_gating import is_feature_gated
        
        features = ['analytics', 'user_groups', 'sso', 'custom_branding', 
                   'api_access', 'advanced_permissions', 'query_history',
                   'usage_reports', 'multi_tenant', 'custom_connectors']
        
        for feature in features:
            assert is_feature_gated(feature) is False
    
    def test_get_gated_features_returns_empty(self):
        """No features should be gated."""
        from myplatform.server.tenants.product_gating import get_gated_features
        
        gated = get_gated_features()
        assert len(gated) == 0
    
    def test_check_feature_access_always_true(self):
        """Feature access should always return True."""
        from myplatform.server.tenants.product_gating import check_feature_access
        
        assert check_feature_access('any_feature') is True
        assert check_feature_access('another_feature', tenant_id='tenant123') is True


class TestTenantProvisioning:
    """Tests for tenant provisioning."""
    
    @patch('myplatform.server.tenants.provisioning.get_session_with_shared_schema')
    def test_get_available_tenant_returns_none(self, mock_session):
        """get_available_tenant should return None in default implementation."""
        from myplatform.server.tenants.provisioning import get_available_tenant
        
        mock_session.return_value.__enter__ = MagicMock()
        mock_session.return_value.__exit__ = MagicMock()
        
        result = get_available_tenant()
        assert result is None


class TestTenantAccess:
    """Tests for tenant access control."""
    
    def test_generate_data_plane_token(self):
        """Should generate a valid JWT token."""
        from myplatform.server.tenants.access import generate_data_plane_token
        
        token = generate_data_plane_token()
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Should verify a valid token."""
        from myplatform.server.tenants.access import (
            generate_data_plane_token,
            verify_data_plane_token,
        )
        
        token = generate_data_plane_token(tenant_id='test_tenant')
        claims = verify_data_plane_token(token)
        
        assert claims is not None
        assert claims.get('tenant_id') == 'test_tenant'
    
    def test_invalid_token_returns_none(self):
        """Invalid token should return None."""
        from myplatform.server.tenants.access import verify_data_plane_token
        
        result = verify_data_plane_token('invalid_token')
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
