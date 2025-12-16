"""
Unit tests for myplatform.db.standard_answers
"""
import pytest
from datetime import datetime

from myplatform.db.standard_answers import (
    CustomStandardAnswer,
    CustomStandardAnswerCategory,
    create_category,
    get_categories,
    create_standard_answer,
    get_standard_answers,
    update_standard_answer,
    delete_standard_answer,
    find_matching_answers,
)


class TestStandardAnswerCategories:
    """Tests for standard answer category operations"""
    
    def test_create_category(self, db_session):
        """Test creating a category"""
        category = create_category(
            db_session,
            name='HR Policies',
            description='Human resources policy questions',
        )
        
        assert category.id is not None
        assert category.name == 'HR Policies'
        assert category.description == 'Human resources policy questions'
    
    def test_create_category_max_length(self, db_session):
        """Test category name length limit"""
        long_name = 'a' * 256  # Exceeds 255 char limit
        
        with pytest.raises(ValueError, match="Category name too long"):
            create_category(db_session, name=long_name)
    
    def test_get_categories(self, db_session):
        """Test getting all categories"""
        create_category(db_session, name='Category 1')
        create_category(db_session, name='Category 2')
        
        categories = get_categories(db_session)
        assert len(categories) >= 2


class TestStandardAnswerCRUD:
    """Tests for standard answer CRUD operations"""
    
    def test_create_standard_answer_keyword(self, db_session):
        """Test creating a keyword-based standard answer"""
        answer = create_standard_answer(
            db_session,
            keyword='password reset',
            answer='To reset your password, go to Settings > Security > Reset Password.',
            match_regex=False,
            match_any_keywords=True,
        )
        
        assert answer.id is not None
        assert answer.keyword == 'password reset'
        assert answer.match_regex is False
        assert answer.active is True
    
    def test_create_standard_answer_regex(self, db_session):
        """Test creating a regex-based standard answer"""
        answer = create_standard_answer(
            db_session,
            keyword=r'(how|what).*(password|login)',
            answer='For login issues, contact IT support.',
            match_regex=True,
        )
        
        assert answer.match_regex is True
    
    def test_create_standard_answer_with_categories(self, db_session):
        """Test creating an answer with categories"""
        cat = create_category(db_session, name='IT Support')
        
        answer = create_standard_answer(
            db_session,
            keyword='VPN setup',
            answer='VPN setup instructions...',
            category_ids=[cat.id],
        )
        
        assert len(answer.categories) == 1
        assert answer.categories[0].id == cat.id
    
    def test_get_standard_answers(self, db_session):
        """Test getting all active standard answers"""
        create_standard_answer(db_session, keyword='test1', answer='Answer 1')
        create_standard_answer(db_session, keyword='test2', answer='Answer 2')
        
        answers = get_standard_answers(db_session, active_only=True)
        assert len(answers) >= 2
    
    def test_update_standard_answer(self, db_session):
        """Test updating a standard answer"""
        answer = create_standard_answer(
            db_session,
            keyword='old keyword',
            answer='old answer',
        )
        
        updated = update_standard_answer(
            db_session,
            answer_id=answer.id,
            keyword='new keyword',
            answer='new answer',
        )
        
        assert updated.keyword == 'new keyword'
        assert updated.answer == 'new answer'
    
    def test_delete_standard_answer(self, db_session):
        """Test soft-deleting a standard answer"""
        answer = create_standard_answer(
            db_session,
            keyword='to delete',
            answer='will be deleted',
        )
        
        result = delete_standard_answer(db_session, answer.id)
        assert result is True
        
        # Verify soft deleted (still exists but inactive)
        updated = db_session.get(CustomStandardAnswer, answer.id)
        assert updated.active is False


class TestStandardAnswerMatching:
    """Tests for query matching logic"""
    
    def test_find_matching_keyword_any(self, db_session):
        """Test matching any keyword in query"""
        create_standard_answer(
            db_session,
            keyword='password reset change',
            answer='Password reset instructions',
            match_any_keywords=True,
        )
        
        matches = find_matching_answers(db_session, 'How do I reset my password?')
        assert len(matches) >= 1
        assert matches[0][0].answer == 'Password reset instructions'
    
    def test_find_matching_keyword_all(self, db_session):
        """Test matching all keywords in query"""
        create_standard_answer(
            db_session,
            keyword='annual leave policy',
            answer='Annual leave policy details...',
            match_any_keywords=False,  # Must match all keywords
        )
        
        # Should match when all keywords present
        matches = find_matching_answers(
            db_session,
            'What is the annual leave policy?',
        )
        assert len(matches) >= 1
    
    def test_find_matching_regex(self, db_session):
        """Test regex pattern matching"""
        create_standard_answer(
            db_session,
            keyword=r'how\s+(do|can)\s+I',
            answer='General help answer',
            match_regex=True,
        )
        
        matches = find_matching_answers(db_session, 'How do I access the portal?')
        assert len(matches) >= 1
    
    def test_find_matching_no_match(self, db_session):
        """Test when no answers match"""
        create_standard_answer(
            db_session,
            keyword='specific rare keyword',
            answer='Specific answer',
        )
        
        matches = find_matching_answers(db_session, 'Completely unrelated query')
        # Should not match
        matching_specific = [m for m in matches if m[0].keyword == 'specific rare keyword']
        assert len(matching_specific) == 0
