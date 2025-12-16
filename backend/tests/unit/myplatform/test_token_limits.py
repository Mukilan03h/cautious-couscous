"""
Unit tests for myplatform.db.token_limits
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from myplatform.db.token_limits import (
    CustomTokenLimit,
    CustomTokenUsage,
    create_token_limit,
    get_token_limits,
    get_user_applicable_limits,
    update_token_limit,
    delete_token_limit,
    get_or_create_usage_record,
    record_token_usage,
    check_token_limit,
)


class TestTokenLimitCRUD:
    """Tests for token limit CRUD operations"""
    
    def test_create_global_token_limit(self, db_session):
        """Test creating a global token limit"""
        limit = create_token_limit(
            db_session,
            token_budget=100000,
            period_hours=24,
            scope='global',
            name='Global Daily Limit',
        )
        
        assert limit.id is not None
        assert limit.scope == 'global'
        assert limit.token_budget == 100000
        assert limit.period_hours == 24
        assert limit.enabled is True
        assert limit.name == 'Global Daily Limit'
    
    def test_create_user_token_limit(self, db_session, sample_user_id):
        """Test creating a user-specific token limit"""
        limit = create_token_limit(
            db_session,
            token_budget=50000,
            period_hours=24,
            scope='user',
            target_user_id=sample_user_id,
        )
        
        assert limit.scope == 'user'
        assert limit.target_user_id == sample_user_id
        assert limit.token_budget == 50000
    
    def test_create_group_token_limit(self, db_session):
        """Test creating a group-specific token limit"""
        # First create a UserGroup to reference
        from esa.db.models import UserGroup
        group = UserGroup(name='Token Limit Test Group')
        db_session.add(group)
        db_session.commit()
        
        limit = create_token_limit(
            db_session,
            token_budget=200000,
            period_hours=168,  # Weekly
            scope='group',
            target_group_id=group.id,
        )
        
        assert limit.scope == 'group'
        assert limit.target_group_id == group.id
        assert limit.period_hours == 168
    
    def test_get_token_limits_all(self, db_session):
        """Test getting all token limits"""
        # Create multiple limits
        create_token_limit(db_session, token_budget=100000, scope='global')
        create_token_limit(db_session, token_budget=50000, scope='user')
        
        limits = get_token_limits(db_session, enabled_only=True)
        assert len(limits) >= 2
    
    def test_get_token_limits_by_scope(self, db_session):
        """Test filtering limits by scope"""
        create_token_limit(db_session, token_budget=100000, scope='global')
        create_token_limit(db_session, token_budget=50000, scope='user')
        
        global_limits = get_token_limits(db_session, scope='global')
        assert all(l.scope == 'global' for l in global_limits)
    
    def test_get_user_applicable_limits(self, db_session, sample_user_id):
        """Test getting limits that apply to a specific user"""
        # Create global limit
        create_token_limit(db_session, token_budget=100000, scope='global')
        # Create user-specific limit
        create_token_limit(
            db_session,
            token_budget=50000,
            scope='user',
            target_user_id=sample_user_id,
        )
        
        applicable = get_user_applicable_limits(db_session, sample_user_id)
        assert len(applicable) >= 2
    
    def test_update_token_limit(self, db_session):
        """Test updating a token limit"""
        limit = create_token_limit(db_session, token_budget=100000, scope='global')
        
        updated = update_token_limit(
            db_session,
            limit_id=limit.id,
            token_budget=200000,
            enabled=False,
        )
        
        assert updated.token_budget == 200000
        assert updated.enabled is False
    
    def test_delete_token_limit(self, db_session):
        """Test deleting a token limit"""
        limit = create_token_limit(db_session, token_budget=100000, scope='global')
        limit_id = limit.id
        
        result = delete_token_limit(db_session, limit_id)
        assert result is True
        
        # Verify deleted
        deleted = db_session.get(CustomTokenLimit, limit_id)
        assert deleted is None


class TestTokenUsageTracking:
    """Tests for token usage tracking"""
    
    def test_get_or_create_usage_record(self, db_session, sample_user_id):
        """Test creating a new usage record"""
        usage = get_or_create_usage_record(db_session, sample_user_id, period_hours=24)
        
        assert usage.user_id == sample_user_id
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.period_end > datetime.utcnow()
    
    def test_record_token_usage(self, db_session, sample_user_id):
        """Test recording token usage"""
        usage = record_token_usage(
            db_session,
            user_id=sample_user_id,
            prompt_tokens=1000,
            completion_tokens=500,
        )
        
        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 500
        
        # Add more tokens
        usage = record_token_usage(
            db_session,
            user_id=sample_user_id,
            prompt_tokens=500,
            completion_tokens=250,
        )
        
        assert usage.prompt_tokens == 1500
        assert usage.completion_tokens == 750
    
    def test_check_token_limit_no_limits(self, db_session, sample_user_id):
        """Test checking limits when none are configured"""
        result = check_token_limit(db_session, sample_user_id)
        
        assert result['allowed'] is True
        assert result['reason'] == 'No limits configured'
    
    def test_check_token_limit_within_budget(self, db_session, sample_user_id):
        """Test checking limits when user is within budget"""
        # Create a limit
        create_token_limit(db_session, token_budget=10000, scope='global')
        
        # Record some usage
        record_token_usage(db_session, sample_user_id, prompt_tokens=1000, completion_tokens=500)
        
        result = check_token_limit(db_session, sample_user_id)
        
        assert result['allowed'] is True
        assert result['total_used'] == 1500
        assert result['remaining'] == 8500
    
    def test_check_token_limit_exceeded(self, db_session, sample_user_id):
        """Test checking limits when user exceeds budget"""
        # Create a small limit
        create_token_limit(db_session, token_budget=1000, scope='global')
        
        # Record usage that exceeds limit
        record_token_usage(db_session, sample_user_id, prompt_tokens=800, completion_tokens=300)
        
        result = check_token_limit(db_session, sample_user_id)
        
        assert result['allowed'] is False
        assert result['total_used'] == 1100
        assert result['remaining'] == 0
