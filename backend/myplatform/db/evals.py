"""
Custom Evals - Answer quality evaluation and testing
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, Boolean, ForeignKey, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from esa.db.models import Base


class CustomEvalDataset(Base):
    """Dataset of question/expected answer pairs for evaluation"""
    __tablename__ = "custom_eval_dataset"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomEvalQuestion(Base):
    """Individual question in an eval dataset"""
    __tablename__ = "custom_eval_question"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("custom_eval_dataset.id"), nullable=False, index=True)
    
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    expected_sources = Column(JSONB, default=[])  # Expected source documents
    category = Column(String, nullable=True)


class CustomEvalRun(Base):
    """A single evaluation run"""
    __tablename__ = "custom_eval_run"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("custom_eval_dataset.id"), nullable=False)
    
    # Run info
    status = Column(String, default='pending')  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Settings used
    persona_id = Column(Integer, nullable=True)
    model_name = Column(String, nullable=True)
    
    # Aggregate scores
    avg_relevance_score = Column(Float, nullable=True)
    avg_accuracy_score = Column(Float, nullable=True)
    total_questions = Column(Integer, default=0)
    passed_questions = Column(Integer, default=0)


class CustomEvalResult(Base):
    """Result for a single question in an eval run"""
    __tablename__ = "custom_eval_result"
    
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("custom_eval_run.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("custom_eval_question.id"), nullable=False)
    
    # Generated answer
    generated_answer = Column(Text, nullable=True)
    sources_used = Column(JSONB, default=[])
    
    # Scores
    relevance_score = Column(Float, nullable=True)  # 0-1
    accuracy_score = Column(Float, nullable=True)  # 0-1
    source_match_score = Column(Float, nullable=True)
    
    # Pass/fail
    passed = Column(Boolean, nullable=True)
    
    # Timing
    response_time_ms = Column(Integer, nullable=True)


# ============ Eval Functions ============

def create_eval_dataset(
    db_session: Session,
    name: str,
    description: str = None,
) -> CustomEvalDataset:
    """Create a new eval dataset"""
    dataset = CustomEvalDataset(name=name, description=description)
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)
    return dataset


def add_eval_question(
    db_session: Session,
    dataset_id: int,
    question: str,
    expected_answer: str = None,
    expected_sources: List[str] = None,
    category: str = None,
) -> CustomEvalQuestion:
    """Add a question to dataset"""
    q = CustomEvalQuestion(
        dataset_id=dataset_id,
        question=question,
        expected_answer=expected_answer,
        expected_sources=expected_sources or [],
        category=category,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def get_dataset_questions(
    db_session: Session,
    dataset_id: int,
) -> List[CustomEvalQuestion]:
    """Get all questions in a dataset"""
    return list(db_session.scalars(
        select(CustomEvalQuestion).where(
            CustomEvalQuestion.dataset_id == dataset_id
        )
    ).all())


def create_eval_run(
    db_session: Session,
    dataset_id: int,
    persona_id: int = None,
    model_name: str = None,
) -> CustomEvalRun:
    """Create a new eval run"""
    run = CustomEvalRun(
        dataset_id=dataset_id,
        persona_id=persona_id,
        model_name=model_name,
        started_at=datetime.utcnow(),
        status='running',
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def record_eval_result(
    db_session: Session,
    run_id: int,
    question_id: int,
    generated_answer: str,
    sources_used: List[str] = None,
    relevance_score: float = None,
    accuracy_score: float = None,
    response_time_ms: int = None,
) -> CustomEvalResult:
    """Record result for a question"""
    passed = (relevance_score or 0) >= 0.7 and (accuracy_score or 0) >= 0.7
    
    result = CustomEvalResult(
        run_id=run_id,
        question_id=question_id,
        generated_answer=generated_answer,
        sources_used=sources_used or [],
        relevance_score=relevance_score,
        accuracy_score=accuracy_score,
        passed=passed,
        response_time_ms=response_time_ms,
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


def complete_eval_run(
    db_session: Session,
    run_id: int,
) -> CustomEvalRun:
    """Complete an eval run and calculate aggregate scores"""
    run = db_session.get(CustomEvalRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")
    
    # Get all results
    results = db_session.scalars(
        select(CustomEvalResult).where(CustomEvalResult.run_id == run_id)
    ).all()
    
    if results:
        run.total_questions = len(results)
        run.passed_questions = sum(1 for r in results if r.passed)
        run.avg_relevance_score = sum(r.relevance_score or 0 for r in results) / len(results)
        run.avg_accuracy_score = sum(r.accuracy_score or 0 for r in results) / len(results)
    
    run.status = 'completed'
    run.completed_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(run)
    return run
