"""
Unit tests for myplatform.db.permissions
"""
import pytest
from uuid import uuid4

from myplatform.db.permissions import (
    CustomDocumentACL,
    set_resource_acl,
    get_resource_acl,
    check_user_access,
    get_accessible_resources,
    add_user_to_acl,
    add_group_to_acl,
    remove_user_from_acl,
    remove_group_from_acl,
)


class TestACLBasics:
    """Tests for basic ACL operations"""
    
    def test_set_resource_acl_create(self, db_session, sample_user_id):
        """Test creating a new ACL for a resource"""
        acl = set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id],
            group_ids=[1, 2],
            is_public=False,
            created_by_id=sample_user_id,
        )
        
        assert acl.id is not None
        assert acl.resource_type == 'document'
        assert acl.resource_id == 1
        assert sample_user_id in acl.user_ids
        assert 1 in acl.group_ids
        assert acl.is_public is False
    
    def test_set_resource_acl_update(self, db_session, sample_user_id, sample_user_id_2):
        """Test updating an existing ACL"""
        # Create initial ACL
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id],
            is_public=False,
        )
        
        # Update ACL
        acl = set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id_2],
            is_public=True,
        )
        
        assert sample_user_id_2 in acl.user_ids
        assert sample_user_id not in acl.user_ids  # Old user replaced
        assert acl.is_public is True
    
    def test_get_resource_acl(self, db_session, sample_user_id):
        """Test retrieving an ACL"""
        set_resource_acl(
            db_session,
            resource_type='persona',
            resource_id=5,
            user_ids=[sample_user_id],
        )
        
        acl = get_resource_acl(db_session, 'persona', 5)
        
        assert acl is not None
        assert acl.resource_type == 'persona'
        assert acl.resource_id == 5
    
    def test_get_resource_acl_not_found(self, db_session):
        """Test retrieving non-existent ACL"""
        acl = get_resource_acl(db_session, 'document', 999)
        assert acl is None


class TestAccessChecks:
    """Tests for access control checks"""
    
    def test_check_user_access_public(self, db_session, sample_user_id):
        """Test access to public resources"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            is_public=True,
        )
        
        has_access = check_user_access(db_session, 'document', 1, sample_user_id)
        assert has_access is True
    
    def test_check_user_access_by_user_id(self, db_session, sample_user_id, sample_user_id_2):
        """Test access granted by user ID"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id],
            is_public=False,
        )
        
        # Granted user has access
        assert check_user_access(db_session, 'document', 1, sample_user_id) is True
        
        # Other user does not
        assert check_user_access(db_session, 'document', 1, sample_user_id_2) is False
    
    def test_check_user_access_by_group(self, db_session, sample_user_id):
        """Test access granted by group membership"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            group_ids=[5, 10],
            is_public=False,
        )
        
        # User in allowed group
        has_access = check_user_access(
            db_session, 'document', 1, sample_user_id, user_group_ids=[5]
        )
        assert has_access is True
        
        # User not in any allowed group
        no_access = check_user_access(
            db_session, 'document', 1, sample_user_id, user_group_ids=[99]
        )
        assert no_access is False
    
    def test_check_user_access_no_acl_is_public(self, db_session, sample_user_id):
        """Test that resources without ACL are accessible (public by default)"""
        has_access = check_user_access(db_session, 'document', 999, sample_user_id)
        assert has_access is True
    
    def test_get_accessible_resources(self, db_session, sample_user_id):
        """Test getting list of accessible resources"""
        # Create various ACLs
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id],
        )
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=2,
            is_public=True,
        )
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=3,
            group_ids=[1, 2],
        )
        
        accessible = get_accessible_resources(
            db_session, 'document', sample_user_id, user_group_ids=[1]
        )
        
        assert 1 in accessible  # Direct user access
        assert 2 in accessible  # Public
        assert 3 in accessible  # Group access


class TestACLModification:
    """Tests for adding/removing users and groups from ACLs"""
    
    def test_add_user_to_acl_new(self, db_session, sample_user_id):
        """Test adding a user to a new ACL"""
        acl = add_user_to_acl(db_session, 'document', 1, sample_user_id)
        
        assert acl.id is not None
        assert sample_user_id in acl.user_ids
    
    def test_add_user_to_acl_existing(self, db_session, sample_user_id, sample_user_id_2):
        """Test adding a user to existing ACL"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id],
        )
        
        acl = add_user_to_acl(db_session, 'document', 1, sample_user_id_2)
        
        assert sample_user_id in acl.user_ids
        assert sample_user_id_2 in acl.user_ids
    
    def test_add_group_to_acl(self, db_session):
        """Test adding a group to ACL"""
        acl = add_group_to_acl(db_session, 'document', 1, 5)
        
        assert 5 in acl.group_ids
    
    def test_remove_user_from_acl(self, db_session, sample_user_id, sample_user_id_2):
        """Test removing a user from ACL"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            user_ids=[sample_user_id, sample_user_id_2],
        )
        
        result = remove_user_from_acl(db_session, 'document', 1, sample_user_id)
        assert result is True
        
        acl = get_resource_acl(db_session, 'document', 1)
        assert sample_user_id not in acl.user_ids
        assert sample_user_id_2 in acl.user_ids
    
    def test_remove_group_from_acl(self, db_session):
        """Test removing a group from ACL"""
        set_resource_acl(
            db_session,
            resource_type='document',
            resource_id=1,
            group_ids=[1, 2, 3],
        )
        
        result = remove_group_from_acl(db_session, 'document', 1, 2)
        assert result is True
        
        acl = get_resource_acl(db_session, 'document', 1)
        assert 2 not in acl.group_ids
        assert 1 in acl.group_ids
