"""
Tests for myplatform external permissions modules.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestConfluencePermissions:
    """Tests for Confluence permission sync."""
    
    def test_constants_defined(self):
        """Verify constants are defined."""
        from myplatform.external_permissions.confluence.constants import (
            ALL_CONF_EMAILS_GROUP_NAME,
            VIEWSPACE_PERMISSION_TYPE,
            REQUEST_PAGINATION_LIMIT,
        )
        
        assert ALL_CONF_EMAILS_GROUP_NAME == "All_Confluence_Users_Found_By_ESA"
        assert VIEWSPACE_PERMISSION_TYPE == "VIEWSPACE"
        assert REQUEST_PAGINATION_LIMIT == 5000
    
    def test_get_page_restrictions_no_restrictions(self):
        """Pages with no restrictions should return None."""
        from myplatform.external_permissions.confluence.page_access import get_page_restrictions
        
        mock_client = MagicMock()
        
        result = get_page_restrictions(
            confluence_client=mock_client,
            page_id="123",
            page_restrictions={},
            ancestors=[],
        )
        
        assert result is None
    
    def test_get_space_permission(self):
        """Should return ExternalAccess for space."""
        from myplatform.external_permissions.confluence.space_access import get_space_permission
        
        mock_client = MagicMock()
        mock_client.get_space.return_value = {"permissions": []}
        
        result = get_space_permission(
            confluence_client=mock_client,
            space_key="TEST",
            is_cloud=True,
        )
        
        assert result is not None


class TestGoogleDrivePermissions:
    """Tests for Google Drive permission sync."""
    
    def test_permission_type_enum(self):
        """Verify permission type enum values."""
        from myplatform.external_permissions.google_drive.models import PermissionType
        
        assert PermissionType.USER.value == "user"
        assert PermissionType.GROUP.value == "group"
        assert PermissionType.DOMAIN.value == "domain"
        assert PermissionType.ANYONE.value == "anyone"
    
    def test_google_drive_permission_from_dict(self):
        """Should create GoogleDrivePermission from dict."""
        from myplatform.external_permissions.google_drive.models import GoogleDrivePermission
        
        perm_dict = {
            "id": "perm123",
            "emailAddress": "user@test.com",
            "type": "user",
            "domain": None,
        }
        
        perm = GoogleDrivePermission.from_drive_permission(perm_dict)
        
        assert perm.id == "perm123"
        assert perm.email_address == "user@test.com"
    
    def test_get_permissions_by_ids_empty(self):
        """Should return empty list for empty permission IDs."""
        from myplatform.external_permissions.google_drive.permission_retrieval import get_permissions_by_ids
        
        mock_service = MagicMock()
        
        result = get_permissions_by_ids(
            drive_service=mock_service,
            doc_id="doc123",
            permission_ids=[],
        )
        
        assert result == []


class TestJiraPermissions:
    """Tests for Jira permission sync."""
    
    def test_permission_model(self):
        """Verify Permission model."""
        from myplatform.external_permissions.jira.models import Permission
        
        perm = Permission(id=1, permission="BROWSE_PROJECTS", holder=None)
        
        assert perm.id == 1
        assert perm.permission == "BROWSE_PROJECTS"
    
    def test_user_model(self):
        """Verify User model with camelCase alias."""
        from myplatform.external_permissions.jira.models import User
        
        user = User(
            account_id="acc123",
            email_address="user@test.com",
            display_name="Test User",
            active=True,
        )
        
        assert user.account_id == "acc123"
        assert user.email_address == "user@test.com"


class TestSlackPermissions:
    """Tests for Slack permission sync."""
    
    def test_get_channel_access_public(self):
        """Public channels should have is_public=True."""
        from myplatform.external_permissions.slack.channel_access import get_channel_access
        
        mock_client = MagicMock()
        channel = {"id": "C123", "is_private": False}
        
        result = get_channel_access(
            client=mock_client,
            channel=channel,
            user_cache={},
        )
        
        assert result.is_public is True
    
    def test_fetch_user_id_to_email_map(self):
        """Should build user ID to email mapping."""
        from myplatform.external_permissions.slack.utils import fetch_user_id_to_email_map
        
        mock_client = MagicMock()
        
        with patch('myplatform.external_permissions.slack.utils.make_paginated_slack_api_call') as mock_call:
            mock_call.return_value = [
                {"members": [{"id": "U123", "profile": {"email": "user@test.com"}}]}
            ]
            
            result = fetch_user_id_to_email_map(mock_client)
        
        assert "U123" in result
        assert result["U123"] == "user@test.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
