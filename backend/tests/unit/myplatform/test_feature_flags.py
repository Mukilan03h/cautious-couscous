"""
Unit tests for myplatform.db.feature_flags
"""
import pytest
from uuid import uuid4

from myplatform.db.feature_flags import (
    CustomFeatureFlag,
    create_feature_flag,
    get_feature_flag,
    get_all_feature_flags,
    update_feature_flag,
    delete_feature_flag,
    is_feature_enabled,
)


class TestFeatureFlagCRUD:
    """Tests for feature flag CRUD operations"""
    
    def test_create_feature_flag(self, db_session):
        """Test creating a feature flag"""
        flag = create_feature_flag(
            db_session,
            name='dark_mode',
            description='Enable dark mode UI',
            enabled_by_default=False,
        )
        
        assert flag.id is not None
        assert flag.name == 'dark_mode'
        assert flag.description == 'Enable dark mode UI'
        assert flag.enabled_by_default is False
        assert flag.enabled_for_all is False
    
    def test_get_feature_flag(self, db_session):
        """Test retrieving a feature flag by name"""
        create_feature_flag(db_session, name='test_flag')
        
        flag = get_feature_flag(db_session, 'test_flag')
        
        assert flag is not None
        assert flag.name == 'test_flag'
    
    def test_get_feature_flag_not_found(self, db_session):
        """Test retrieving non-existent flag"""
        flag = get_feature_flag(db_session, 'nonexistent')
        assert flag is None
    
    def test_get_all_feature_flags(self, db_session):
        """Test getting all feature flags"""
        create_feature_flag(db_session, name='flag1')
        create_feature_flag(db_session, name='flag2')
        
        flags = get_all_feature_flags(db_session)
        flag_names = [f.name for f in flags]
        
        assert 'flag1' in flag_names
        assert 'flag2' in flag_names
    
    def test_update_feature_flag_enable_for_all(self, db_session):
        """Test enabling a flag for all users"""
        create_feature_flag(db_session, name='global_flag')
        
        updated = update_feature_flag(
            db_session,
            name='global_flag',
            enabled_for_all=True,
        )
        
        assert updated.enabled_for_all is True
    
    def test_update_feature_flag_target_users(self, db_session, sample_user_id):
        """Test targeting specific users"""
        create_feature_flag(db_session, name='beta_feature')
        
        updated = update_feature_flag(
            db_session,
            name='beta_feature',
            enabled_user_ids=[sample_user_id],
        )
        
        assert sample_user_id in updated.enabled_user_ids
    
    def test_delete_feature_flag(self, db_session):
        """Test deleting a feature flag"""
        create_feature_flag(db_session, name='temp_flag')
        
        result = delete_feature_flag(db_session, 'temp_flag')
        assert result is True
        
        flag = get_feature_flag(db_session, 'temp_flag')
        assert flag is None


class TestFeatureFlagEvaluation:
    """Tests for feature flag evaluation logic"""
    
    def test_is_feature_enabled_unknown_flag(self, db_session, sample_user_id):
        """Test that unknown flags are disabled"""
        enabled = is_feature_enabled(db_session, 'unknown_flag', user_id=sample_user_id)
        assert enabled is False
    
    def test_is_feature_enabled_by_default(self, db_session, sample_user_id):
        """Test flag enabled by default"""
        create_feature_flag(
            db_session,
            name='default_on',
            enabled_by_default=True,
        )
        
        enabled = is_feature_enabled(db_session, 'default_on', user_id=sample_user_id)
        assert enabled is True
    
    def test_is_feature_enabled_for_all(self, db_session, sample_user_id):
        """Test flag enabled for all users"""
        create_feature_flag(db_session, name='global_feature')
        update_feature_flag(db_session, 'global_feature', enabled_for_all=True)
        
        enabled = is_feature_enabled(db_session, 'global_feature', user_id=sample_user_id)
        assert enabled is True
    
    def test_is_feature_enabled_for_specific_user(self, db_session, sample_user_id, sample_user_id_2):
        """Test flag enabled for specific users"""
        create_feature_flag(db_session, name='user_feature')
        update_feature_flag(
            db_session,
            'user_feature',
            enabled_user_ids=[sample_user_id],
        )
        
        # Enabled user
        assert is_feature_enabled(db_session, 'user_feature', user_id=sample_user_id) is True
        
        # Not enabled user
        assert is_feature_enabled(db_session, 'user_feature', user_id=sample_user_id_2) is False
    
    def test_is_feature_enabled_for_group(self, db_session, sample_user_id):
        """Test flag enabled for specific groups"""
        create_feature_flag(db_session, name='group_feature')
        update_feature_flag(
            db_session,
            'group_feature',
            enabled_group_ids=[1, 2],
        )
        
        # User in enabled group
        assert is_feature_enabled(
            db_session, 'group_feature', user_id=sample_user_id, group_ids=[1]
        ) is True
        
        # User not in enabled group
        assert is_feature_enabled(
            db_session, 'group_feature', user_id=sample_user_id, group_ids=[99]
        ) is False
    
    def test_is_feature_enabled_explicit_disable_overrides(self, db_session, sample_user_id):
        """Test that explicit disable overrides enables"""
        create_feature_flag(db_session, name='override_test')
        update_feature_flag(
            db_session,
            'override_test',
            enabled_for_all=True,
            disabled_user_ids=[sample_user_id],
        )
        
        # Disabled user even though enabled for all
        assert is_feature_enabled(db_session, 'override_test', user_id=sample_user_id) is False
    
    def test_is_feature_enabled_tenant_targeting(self, db_session, sample_user_id):
        """Test flag enabled for specific tenants"""
        create_feature_flag(db_session, name='tenant_feature')
        update_feature_flag(
            db_session,
            'tenant_feature',
            enabled_tenant_ids=[1, 2],
        )
        
        assert is_feature_enabled(
            db_session, 'tenant_feature', user_id=sample_user_id, tenant_id=1
        ) is True
        
        assert is_feature_enabled(
            db_session, 'tenant_feature', user_id=sample_user_id, tenant_id=99
        ) is False
