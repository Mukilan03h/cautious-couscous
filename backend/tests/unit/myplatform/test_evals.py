"""
Unit tests for myplatform.db.evals
"""
import pytest
from datetime import datetime

from myplatform.db.evals import (
    CustomEvalDataset,
    CustomEvalQuestion,
    CustomEvalRun,
    CustomEvalResult,
    create_eval_dataset,
    add_eval_question,
    get_dataset_questions,
    create_eval_run,
    record_eval_result,
    complete_eval_run,
)


class TestEvalDatasetManagement:
    """Tests for evaluation dataset management"""
    
    def test_create_eval_dataset(self, db_session):
        """Test creating an evaluation dataset"""
        dataset = create_eval_dataset(
            db_session,
            name='HR Policy Test',
            description='Tests for HR policy questions',
        )
        
        assert dataset.id is not None
        assert dataset.name == 'HR Policy Test'
        assert dataset.description == 'Tests for HR policy questions'
    
    def test_add_eval_question(self, db_session):
        """Test adding a question to a dataset"""
        dataset = create_eval_dataset(db_session, name='Test Dataset')
        
        question = add_eval_question(
            db_session,
            dataset_id=dataset.id,
            question='What is the vacation policy?',
            expected_answer='Employees get 20 days of paid vacation per year.',
            expected_sources=['hr_handbook.pdf'],
            category='HR',
        )
        
        assert question.id is not None
        assert question.dataset_id == dataset.id
        assert question.question == 'What is the vacation policy?'
        assert question.expected_answer == 'Employees get 20 days of paid vacation per year.'
        assert question.category == 'HR'
    
    def test_get_dataset_questions(self, db_session):
        """Test retrieving all questions for a dataset"""
        dataset = create_eval_dataset(db_session, name='Multi Question Dataset')
        
        add_eval_question(db_session, dataset.id, 'Question 1')
        add_eval_question(db_session, dataset.id, 'Question 2')
        add_eval_question(db_session, dataset.id, 'Question 3')
        
        questions = get_dataset_questions(db_session, dataset.id)
        
        assert len(questions) == 3


class TestEvalRunExecution:
    """Tests for running evaluations"""
    
    def test_create_eval_run(self, db_session):
        """Test creating an evaluation run"""
        dataset = create_eval_dataset(db_session, name='Run Test Dataset')
        
        run = create_eval_run(
            db_session,
            dataset_id=dataset.id,
            persona_id=1,
            model_name='gpt-4',
        )
        
        assert run.id is not None
        assert run.dataset_id == dataset.id
        assert run.status == 'running'
        assert run.started_at is not None
        assert run.persona_id == 1
        assert run.model_name == 'gpt-4'
    
    def test_record_eval_result(self, db_session):
        """Test recording a result for a question"""
        dataset = create_eval_dataset(db_session, name='Result Test')
        question = add_eval_question(db_session, dataset.id, 'Test question')
        run = create_eval_run(db_session, dataset.id)
        
        result = record_eval_result(
            db_session,
            run_id=run.id,
            question_id=question.id,
            generated_answer='The answer is...',
            sources_used=['doc1.pdf', 'doc2.pdf'],
            relevance_score=0.9,
            accuracy_score=0.85,
            response_time_ms=500,
        )
        
        assert result.id is not None
        assert result.generated_answer == 'The answer is...'
        assert result.relevance_score == 0.9
        assert result.accuracy_score == 0.85
        assert result.passed is True  # Both scores >= 0.7
    
    def test_record_eval_result_failing(self, db_session):
        """Test recording a failing result"""
        dataset = create_eval_dataset(db_session, name='Fail Test')
        question = add_eval_question(db_session, dataset.id, 'Hard question')
        run = create_eval_run(db_session, dataset.id)
        
        result = record_eval_result(
            db_session,
            run_id=run.id,
            question_id=question.id,
            generated_answer='Incorrect answer',
            relevance_score=0.5,  # Below threshold
            accuracy_score=0.4,   # Below threshold
        )
        
        assert result.passed is False
    
    def test_complete_eval_run(self, db_session):
        """Test completing an evaluation run with summary"""
        dataset = create_eval_dataset(db_session, name='Complete Test')
        run = create_eval_run(db_session, dataset.id)
        
        # Add some questions and results
        for i in range(5):
            q = add_eval_question(db_session, dataset.id, f'Question {i}')
            record_eval_result(
                db_session,
                run.id,
                q.id,
                generated_answer=f'Answer {i}',
                relevance_score=0.8 if i < 4 else 0.5,
                accuracy_score=0.8 if i < 4 else 0.5,
            )
        
        completed_run = complete_eval_run(db_session, run.id)
        
        assert completed_run.status == 'completed'
        assert completed_run.completed_at is not None
        assert completed_run.total_questions == 5
        assert completed_run.passed_questions == 4  # 4 passed, 1 failed
        assert completed_run.avg_relevance_score is not None
        assert completed_run.avg_accuracy_score is not None


class TestEvalResultScoring:
    """Tests for scoring logic"""
    
    def test_passing_threshold(self, db_session):
        """Test that pass threshold is correctly applied"""
        dataset = create_eval_dataset(db_session, name='Threshold Test')
        question = add_eval_question(db_session, dataset.id, 'Test Q')
        run = create_eval_run(db_session, dataset.id)
        
        # Just at threshold - should pass
        result_pass = record_eval_result(
            db_session, run.id, question.id,
            generated_answer='answer',
            relevance_score=0.7,
            accuracy_score=0.7,
        )
        assert result_pass.passed is True
        
        # Just below threshold - should fail
        q2 = add_eval_question(db_session, dataset.id, 'Test Q2')
        result_fail = record_eval_result(
            db_session, run.id, q2.id,
            generated_answer='answer',
            relevance_score=0.69,
            accuracy_score=0.7,
        )
        assert result_fail.passed is False
