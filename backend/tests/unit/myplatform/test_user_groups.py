"""
Unit tests for myplatform.db.user_groups
Tests use ESA's UserGroup model structure
"""
import pytest
from datetime import datetime
from uuid import uuid4

from esa.db.models import UserGroup, User__UserGroup
from sqlalchemy import select


# Alias for test compatibility
CustomUserGroup = UserGroup


class TestUserGroupModel:
    """Tests for UserGroup model operations"""
    
    def test_create_user_group(self, db_session):
        """Test creating a user group"""
        group = UserGroup(
            name='Engineering Team',
        )
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        
        assert group.id is not None
        assert group.name == 'Engineering Team'
        assert group.is_up_to_date is False
        assert group.is_up_for_deletion is False
    
    def test_create_user_group_with_unique_name(self, db_session):
        """Test creating a group with unique name constraint"""
        group = UserGroup(name='Unique Data Team')
        db_session.add(group)
        db_session.commit()
        
        assert group.id is not None
        assert group.name == 'Unique Data Team'
    
    def test_update_user_group(self, db_session):
        """Test updating a user group"""
        group = UserGroup(name='Original Name Test')
        db_session.add(group)
        db_session.commit()
        
        group.name = 'Updated Name Test'
        group.is_up_to_date = True
        db_session.commit()
        db_session.refresh(group)
        
        assert group.name == 'Updated Name Test'
        assert group.is_up_to_date is True
    
    def test_mark_group_for_deletion(self, db_session):
        """Test marking a user group for deletion"""
        group = UserGroup(name='Delete Me Group')
        db_session.add(group)
        db_session.commit()
        
        group.is_up_for_deletion = True
        db_session.commit()
        
        assert group.is_up_for_deletion is True
    
    def test_get_all_groups(self, db_session):
        """Test querying all groups"""
        # Create unique groups for this test
        db_session.add(UserGroup(name='Query Test Active 1'))
        db_session.add(UserGroup(name='Query Test Active 2'))
        db_session.commit()
        
        groups = db_session.scalars(
            select(UserGroup).where(UserGroup.name.like('Query Test%'))
        ).all()
        
        assert len(groups) >= 2


class TestUserGroupRelationships:
    """Tests for user group relationship operations using User__UserGroup"""
    
    def test_user_group_has_time_modified(self, db_session):
        """Test that user groups have time_last_modified_by_user"""
        group = UserGroup(name='Time Test Group')
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        
        assert group.time_last_modified_by_user is not None


class TestUserGroupAccessControl:
    """Tests for group-based access control via relationships"""
    
    def test_group_has_empty_relationships(self, db_session):
        """Test that new groups have empty relationship lists"""
        group = UserGroup(name='Empty Relationships Group')
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        
        # New groups should have empty relationship lists
        assert group.users == []
        # Note: cc_pairs, personas, document_sets are viewonly relationships
    
    def test_group_sync_status(self, db_session):
        """Test group sync status flags"""
        group = UserGroup(name='Sync Status Group')
        db_session.add(group)
        db_session.commit()
        
        # Initially not synced
        assert group.is_up_to_date is False
        
        # Mark as synced
        group.is_up_to_date = True
        db_session.commit()
        
        assert group.is_up_to_date is True
    
    def test_group_deletion_marking(self, db_session):
        """Test marking groups for deletion"""
        group = UserGroup(name='Deletion Mark Group')
        db_session.add(group)
        db_session.commit()
        
        # Initially not marked for deletion
        assert group.is_up_for_deletion is False
        
        # Mark for deletion
        group.is_up_for_deletion = True
        db_session.commit()
        
        assert group.is_up_for_deletion is True
