"""
Unit tests for myplatform.db.analytics
"""
import pytest
from datetime import datetime
from uuid import uuid4

from myplatform.db.analytics import (
    CustomUsageStats,
    CustomUserActivity,
)
from sqlalchemy import select


class TestUsageStatsModel:
    """Tests for daily usage statistics"""
    
    def test_create_usage_stats(self, db_session):
        """Test creating daily usage stats"""
        stats = CustomUsageStats(
            date=datetime.utcnow(),
            total_chats=100,
            total_messages=500,
            unique_users=25,
            total_prompt_tokens=50000,
            total_completion_tokens=40000,
            total_searches=200,
            avg_search_latency_ms=150.5,
            total_documents_indexed=1000,
        )
        db_session.add(stats)
        db_session.commit()
        
        assert stats.id is not None
        assert stats.total_chats == 100
        assert stats.total_messages == 500
        assert stats.unique_users == 25
        assert stats.total_prompt_tokens == 50000
    
    def test_query_usage_stats_by_date(self, db_session):
        """Test querying stats by date range"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = CustomUsageStats(
            date=today,
            total_chats=50,
            total_messages=200,
        )
        db_session.add(stats)
        db_session.commit()
        
        result = db_session.scalars(
            select(CustomUsageStats)
            .where(CustomUsageStats.date >= today)
        ).all()
        
        assert len(result) >= 1
        assert result[0].total_chats == 50
    
    def test_update_usage_stats(self, db_session):
        """Test updating usage stats"""
        stats = CustomUsageStats(
            date=datetime.utcnow(),
            total_chats=10,
        )
        db_session.add(stats)
        db_session.commit()
        
        stats.total_chats = 20
        stats.total_messages = 100
        db_session.commit()
        
        assert stats.total_chats == 20
        assert stats.total_messages == 100


class TestUserActivityModel:
    """Tests for per-user activity tracking"""
    
    def test_create_user_activity(self, db_session, sample_user_id):
        """Test creating user activity record"""
        activity = CustomUserActivity(
            user_id=sample_user_id,
            date=datetime.utcnow(),
            chat_count=5,
            message_count=25,
            search_count=10,
            document_uploads=2,
            prompt_tokens=5000,
            completion_tokens=4000,
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.id is not None
        assert activity.chat_count == 5
        assert activity.message_count == 25
    
    def test_query_user_activity(self, db_session, sample_user_id):
        """Test querying activity for a specific user"""
        activity = CustomUserActivity(
            user_id=sample_user_id,
            date=datetime.utcnow(),
            chat_count=3,
        )
        db_session.add(activity)
        db_session.commit()
        
        result = db_session.scalars(
            select(CustomUserActivity)
            .where(CustomUserActivity.user_id == sample_user_id)
        ).all()
        
        assert len(result) >= 1
    
    def test_aggregate_user_activity(self, db_session, sample_user_id):
        """Test aggregating user activity across days"""
        from sqlalchemy import func
        
        for i in range(5):
            db_session.add(CustomUserActivity(
                user_id=sample_user_id,
                date=datetime.utcnow(),
                chat_count=10,
                message_count=50,
            ))
        db_session.commit()
        
        total_chats = db_session.scalar(
            select(func.sum(CustomUserActivity.chat_count))
            .where(CustomUserActivity.user_id == sample_user_id)
        )
        
        assert total_chats >= 50


class TestAnalyticsDefaults:
    """Tests for analytics model defaults"""
    
    def test_usage_stats_defaults(self, db_session):
        """Test that usage stats have correct defaults"""
        stats = CustomUsageStats(date=datetime.utcnow())
        db_session.add(stats)
        db_session.commit()
        
        assert stats.total_chats == 0
        assert stats.total_messages == 0
        assert stats.unique_users == 0
        assert stats.total_prompt_tokens == 0
        assert stats.total_completion_tokens == 0
        assert stats.total_searches == 0
        assert stats.avg_search_latency_ms == 0
        assert stats.total_documents_indexed == 0
    
    def test_user_activity_defaults(self, db_session, sample_user_id):
        """Test that user activity has correct defaults"""
        activity = CustomUserActivity(
            user_id=sample_user_id,
            date=datetime.utcnow(),
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.chat_count == 0
        assert activity.message_count == 0
        assert activity.search_count == 0
        assert activity.document_uploads == 0
        assert activity.prompt_tokens == 0
        assert activity.completion_tokens == 0
