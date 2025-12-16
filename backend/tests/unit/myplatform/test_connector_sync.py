"""
Unit tests for myplatform.db.connector_permissions
"""
import pytest
from datetime import datetime
from uuid import uuid4

from myplatform.db.connector_permissions import (
    CustomConnectorPermissionSync,
    CustomExternalUserMapping,
    CustomExternalResourcePermission,
    enable_connector_sync,
    get_connector_sync_status,
    update_sync_status,
    map_external_user,
    store_external_permissions,
    check_external_access,
)


class TestConnectorSyncStatus:
    """Tests for connector sync status management"""
    
    def test_enable_connector_sync(self, db_session):
        """Test enabling sync for a connector"""
        sync = enable_connector_sync(
            db_session,
            connector_id=1,
            connector_type='slack',
            sync_config={'channel_filter': ['general', 'engineering']},
        )
        
        assert sync.id is not None
        assert sync.connector_id == 1
        assert sync.connector_type == 'slack'
        assert sync.sync_enabled is True
        assert sync.sync_status == 'pending'
        assert sync.sync_config == {'channel_filter': ['general', 'engineering']}
    
    def test_enable_connector_sync_update(self, db_session):
        """Test updating sync config for existing connector"""
        enable_connector_sync(db_session, connector_id=1, connector_type='slack')
        
        sync = enable_connector_sync(
            db_session,
            connector_id=1,
            connector_type='slack',
            sync_config={'new_setting': True},
        )
        
        assert sync.sync_config == {'new_setting': True}
    
    def test_get_connector_sync_status(self, db_session):
        """Test getting sync status"""
        enable_connector_sync(db_session, connector_id=5, connector_type='google_drive')
        
        status = get_connector_sync_status(db_session, 5)
        
        assert status is not None
        assert status.connector_id == 5
    
    def test_get_connector_sync_status_not_found(self, db_session):
        """Test getting status for non-existent connector"""
        status = get_connector_sync_status(db_session, 999)
        assert status is None
    
    def test_update_sync_status_success(self, db_session):
        """Test updating sync status to success"""
        enable_connector_sync(db_session, connector_id=1, connector_type='jira')
        
        update_sync_status(db_session, 1, 'success')
        
        status = get_connector_sync_status(db_session, 1)
        assert status.sync_status == 'success'
        assert status.last_sync_at is not None
    
    def test_update_sync_status_error(self, db_session):
        """Test updating sync status with error"""
        enable_connector_sync(db_session, connector_id=1, connector_type='confluence')
        
        update_sync_status(db_session, 1, 'error', 'Connection timeout')
        
        status = get_connector_sync_status(db_session, 1)
        assert status.sync_status == 'error'
        assert status.last_error == 'Connection timeout'


class TestExternalUserMapping:
    """Tests for external user mapping"""
    
    def test_map_external_user(self, db_session, sample_user_id):
        """Test mapping an external user ID"""
        mapping = map_external_user(
            db_session,
            user_id=sample_user_id,
            connector_type='slack',
            external_user_id='U12345ABC',
            external_email='john@example.com',
            external_name='John Doe',
        )
        
        assert mapping.id is not None
        assert mapping.user_id == sample_user_id
        assert mapping.connector_type == 'slack'
        assert mapping.external_user_id == 'U12345ABC'
        assert mapping.external_email == 'john@example.com'
    
    def test_map_external_user_update(self, db_session, sample_user_id):
        """Test updating an external mapping"""
        map_external_user(
            db_session,
            user_id=sample_user_id,
            connector_type='slack',
            external_user_id='OLD123',
        )
        
        mapping = map_external_user(
            db_session,
            user_id=sample_user_id,
            connector_type='slack',
            external_user_id='NEW456',
        )
        
        assert mapping.external_user_id == 'NEW456'
        assert mapping.last_verified_at is not None


class TestExternalResourcePermissions:
    """Tests for storing external resource permissions"""
    
    def test_store_external_permissions(self, db_session):
        """Test storing permissions from external source"""
        perm = store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C12345',
            resource_type='channel',
            resource_name='general',
            allowed_user_ids=['U1', 'U2', 'U3'],
            is_public=False,
        )
        
        assert perm.id is not None
        assert perm.resource_id == 'C12345'
        assert perm.resource_name == 'general'
        assert 'U1' in perm.allowed_external_user_ids
    
    def test_store_external_permissions_update(self, db_session):
        """Test updating external permissions"""
        store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C12345',
            resource_type='channel',
            allowed_user_ids=['U1'],
        )
        
        perm = store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C12345',
            resource_type='channel',
            allowed_user_ids=['U1', 'U2', 'U3'],
        )
        
        assert len(perm.allowed_external_user_ids) == 3


class TestExternalAccessCheck:
    """Tests for checking access based on external permissions"""
    
    def test_check_external_access_no_permissions(self, db_session, sample_user_id):
        """Test access when no permissions are stored (allows by default)"""
        has_access = check_external_access(
            db_session,
            connector_id=1,
            resource_id='unknown_resource',
            user_id=sample_user_id,
        )
        
        assert has_access is True
    
    def test_check_external_access_public(self, db_session, sample_user_id):
        """Test access to public resource"""
        store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C_PUBLIC',
            resource_type='channel',
            is_public=True,
        )
        
        has_access = check_external_access(
            db_session,
            connector_id=1,
            resource_id='C_PUBLIC',
            user_id=sample_user_id,
        )
        
        assert has_access is True
    
    def test_check_external_access_with_mapping(self, db_session, sample_user_id):
        """Test access when user has correct external mapping"""
        # Store external permissions
        store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C_PRIVATE',
            resource_type='channel',
            allowed_user_ids=['U12345'],
            is_public=False,
        )
        
        # Map user to external ID
        map_external_user(
            db_session,
            user_id=sample_user_id,
            connector_type='slack',
            external_user_id='U12345',
        )
        
        has_access = check_external_access(
            db_session,
            connector_id=1,
            resource_id='C_PRIVATE',
            user_id=sample_user_id,
        )
        
        assert has_access is True
    
    def test_check_external_access_denied(self, db_session, sample_user_id):
        """Test access denied when user not in allowed list"""
        store_external_permissions(
            db_session,
            connector_id=1,
            connector_type='slack',
            resource_id='C_RESTRICTED',
            resource_type='channel',
            allowed_user_ids=['U_OTHER'],
            is_public=False,
        )
        
        map_external_user(
            db_session,
            user_id=sample_user_id,
            connector_type='slack',
            external_user_id='U_DIFFERENT',
        )
        
        has_access = check_external_access(
            db_session,
            connector_id=1,
            resource_id='C_RESTRICTED',
            user_id=sample_user_id,
        )
        
        assert has_access is False
