"""
Unit tests for myplatform.db.query_history
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from myplatform.db.query_history import (
    CustomQueryLog,
    log_query,
    get_query_history,
    get_query_count,
    update_query_feedback,
    get_feedback_summary,
)


class TestQueryLogging:
    """Tests for query logging operations"""
    
    def test_log_query_basic(self, db_session, sample_user_id):
        """Test logging a basic query"""
        log_entry = log_query(
            db_session,
            query_text='What is the company policy on remote work?',
            user_id=sample_user_id,
        )
        
        assert log_entry.id is not None
        assert log_entry.query_text == 'What is the company policy on remote work?'
        assert log_entry.user_id == sample_user_id
        assert log_entry.timestamp is not None
    
    def test_log_query_with_response(self, db_session, sample_user_id):
        """Test logging a query with response metadata"""
        log_entry = log_query(
            db_session,
            query_text='How do I reset my password?',
            user_id=sample_user_id,
            response_text='To reset your password, go to Settings...',
            response_time_ms=150,
            prompt_tokens=50,
            completion_tokens=100,
            documents_retrieved=5,
            sources_cited=2,
            model_name='gpt-4',
        )
        
        assert log_entry.response_text == 'To reset your password, go to Settings...'
        assert log_entry.response_time_ms == 150
        assert log_entry.prompt_tokens == 50
        assert log_entry.completion_tokens == 100
        assert log_entry.documents_retrieved == 5
        assert log_entry.sources_cited == 2
        assert log_entry.model_name == 'gpt-4'
    
    def test_log_query_with_metadata(self, db_session, sample_user_id):
        """Test logging a query with custom metadata"""
        log_entry = log_query(
            db_session,
            query_text='Test query',
            user_id=sample_user_id,
            extra_metadata={'persona_id': 1, 'filters': ['hr', 'policy']},
        )
        
        assert log_entry.extra_metadata == {'persona_id': 1, 'filters': ['hr', 'policy']}


class TestQueryHistoryRetrieval:
    """Tests for retrieving query history"""
    
    def test_get_query_history_all(self, db_session, sample_user_id):
        """Test getting all query history"""
        log_query(db_session, query_text='Query 1', user_id=sample_user_id)
        log_query(db_session, query_text='Query 2', user_id=sample_user_id)
        log_query(db_session, query_text='Query 3', user_id=sample_user_id)
        
        history = get_query_history(db_session)
        assert len(history) >= 3
    
    def test_get_query_history_by_user(self, db_session, sample_user_id, sample_user_id_2):
        """Test filtering history by user"""
        log_query(db_session, query_text='User 1 query', user_id=sample_user_id)
        log_query(db_session, query_text='User 2 query', user_id=sample_user_id_2)
        
        history = get_query_history(db_session, user_id=sample_user_id)
        assert all(q.user_id == sample_user_id for q in history)
    
    def test_get_query_history_pagination(self, db_session, sample_user_id):
        """Test pagination of query history"""
        for i in range(15):
            log_query(db_session, query_text=f'Query {i}', user_id=sample_user_id)
        
        page1 = get_query_history(db_session, page=0, page_size=10)
        page2 = get_query_history(db_session, page=1, page_size=10)
        
        assert len(page1) == 10
        assert len(page2) >= 5
    
    def test_get_query_history_with_feedback_filter(self, db_session, sample_user_id):
        """Test filtering by feedback presence"""
        entry = log_query(db_session, query_text='Rated query', user_id=sample_user_id)
        log_query(db_session, query_text='Unrated query', user_id=sample_user_id)
        
        # Add feedback to one entry
        update_query_feedback(db_session, entry.id, is_positive=True)
        
        with_feedback = get_query_history(db_session, has_feedback=True)
        without_feedback = get_query_history(db_session, has_feedback=False)
        
        assert any(q.feedback_positive is not None for q in with_feedback)
    
    def test_get_query_count(self, db_session, sample_user_id):
        """Test getting query count"""
        for i in range(5):
            log_query(db_session, query_text=f'Query {i}', user_id=sample_user_id)
        
        count = get_query_count(db_session, user_id=sample_user_id)
        assert count >= 5


class TestFeedback:
    """Tests for feedback functionality"""
    
    def test_update_query_feedback_positive(self, db_session, sample_user_id):
        """Test adding positive feedback"""
        entry = log_query(db_session, query_text='Good response', user_id=sample_user_id)
        
        updated = update_query_feedback(
            db_session,
            query_id=entry.id,
            is_positive=True,
            feedback_text='Very helpful!',
        )
        
        assert updated.feedback_positive is True
        assert updated.feedback_text == 'Very helpful!'
    
    def test_update_query_feedback_negative(self, db_session, sample_user_id):
        """Test adding negative feedback"""
        entry = log_query(db_session, query_text='Bad response', user_id=sample_user_id)
        
        updated = update_query_feedback(
            db_session,
            query_id=entry.id,
            is_positive=False,
            feedback_text='Answer was incorrect',
        )
        
        assert updated.feedback_positive is False
    
    def test_get_feedback_summary(self, db_session, sample_user_id):
        """Test getting feedback summary statistics"""
        # Create entries with various feedback
        for i in range(5):
            entry = log_query(db_session, query_text=f'Query {i}', user_id=sample_user_id)
            if i < 3:
                update_query_feedback(db_session, entry.id, is_positive=True)
            elif i == 3:
                update_query_feedback(db_session, entry.id, is_positive=False)
            # Leave one without feedback
        
        summary = get_feedback_summary(db_session)
        
        assert summary['total_queries'] >= 5
        assert summary['positive_feedback'] >= 3
        assert summary['negative_feedback'] >= 1
        assert 'satisfaction_rate' in summary
