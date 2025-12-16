"""
Tests for myplatform access module.
"""
import pytest
from unittest.mock import MagicMock, patch

from myplatform.access.access import (
    get_access_for_document,
    build_access_control_list,
    get_acl_for_user,
)


class TestGetAccessForDocument:
    """Tests for get_access_for_document function."""
    
    def test_public_document_returns_none(self):
        """Public documents should return None for access control."""
        doc = MagicMock()
        doc.is_public = True
        
        access = get_access_for_document(doc)
        assert access is None or access.is_public
    
    def test_document_with_user_emails(self):
        """Documents with user ACL should return user emails."""
        doc = MagicMock()
        doc.is_public = False
        doc.external_user_emails = ["user1@example.com", "user2@example.com"]
        doc.external_user_group_ids = []
        
        access = get_access_for_document(doc)
        assert access is not None
        assert "user1@example.com" in access.external_user_emails
    
    def test_document_with_groups(self):
        """Documents with group ACL should return group IDs."""
        doc = MagicMock()
        doc.is_public = False
        doc.external_user_emails = []
        doc.external_user_group_ids = ["group1", "group2"]
        
        access = get_access_for_document(doc)
        assert access is not None
        assert "group1" in access.external_user_group_ids


class TestBuildAccessControlList:
    """Tests for build_access_control_list function."""
    
    def test_build_acl_with_user(self):
        """Building ACL for a user should include user email."""
        user = MagicMock()
        user.email = "test@example.com"
        user.groups = []
        
        with patch('myplatform.access.access.get_external_groups_for_user') as mock_groups:
            mock_groups.return_value = set()
            acl = build_access_control_list(user)
        
        assert user.email in acl
    
    def test_build_acl_with_groups(self):
        """Building ACL should include user's group memberships."""
        user = MagicMock()
        user.email = "test@example.com"
        
        group = MagicMock()
        group.name = "engineering"
        user.groups = [group]
        
        with patch('myplatform.access.access.get_external_groups_for_user') as mock_groups:
            mock_groups.return_value = set()
            acl = build_access_control_list(user)
        
        assert "engineering" in acl or any("engineering" in item for item in acl)


class TestGetAclForUser:
    """Tests for get_acl_for_user function."""
    
    def test_acl_includes_user_email(self):
        """ACL should include the user's email."""
        user = MagicMock()
        user.email = "test@example.com"
        user.id = "user-123"
        user.groups = []
        
        with patch('myplatform.access.access.get_external_groups_for_user') as mock_groups:
            mock_groups.return_value = set()
            acl = get_acl_for_user(user)
        
        assert user.email in acl


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
