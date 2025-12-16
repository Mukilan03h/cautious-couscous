"""
Custom Evals API - Answer quality testing
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.evals import (
    create_eval_dataset,
    add_eval_question,
    get_dataset_questions,
    create_eval_run,
    complete_eval_run,
    CustomEvalDataset,
    CustomEvalRun,
)


router = APIRouter(prefix="/api/admin/evals", tags=["evals"])


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None


class QuestionCreate(BaseModel):
    question: str
    expected_answer: Optional[str] = None
    expected_sources: List[str] = []
    category: Optional[str] = None


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class QuestionResponse(BaseModel):
    id: int
    question: str
    expected_answer: Optional[str]
    category: Optional[str]


class RunCreate(BaseModel):
    dataset_id: int
    persona_id: Optional[int] = None
    model_name: Optional[str] = None


class RunResponse(BaseModel):
    id: int
    dataset_id: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    avg_relevance_score: Optional[float]
    avg_accuracy_score: Optional[float]
    total_questions: int
    passed_questions: int


# ============ Dataset Endpoints ============

@router.post("/datasets", response_model=DatasetResponse)
def create_dataset(
    dataset: DatasetCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new eval dataset"""
    d = create_eval_dataset(db, dataset.name, dataset.description)
    return DatasetResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        created_at=d.created_at,
    )


@router.post("/datasets/{dataset_id}/questions", response_model=QuestionResponse)
def add_question(
    dataset_id: int,
    question: QuestionCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Add question to dataset"""
    q = add_eval_question(
        db,
        dataset_id=dataset_id,
        question=question.question,
        expected_answer=question.expected_answer,
        expected_sources=question.expected_sources,
        category=question.category,
    )
    return QuestionResponse(
        id=q.id,
        question=q.question,
        expected_answer=q.expected_answer,
        category=q.category,
    )


@router.get("/datasets/{dataset_id}/questions", response_model=List[QuestionResponse])
def list_questions(
    dataset_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List questions in dataset"""
    questions = get_dataset_questions(db, dataset_id)
    return [
        QuestionResponse(
            id=q.id,
            question=q.question,
            expected_answer=q.expected_answer,
            category=q.category,
        )
        for q in questions
    ]


# ============ Run Endpoints ============

@router.post("/runs", response_model=RunResponse)
def start_eval_run(
    run: RunCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Start a new eval run"""
    r = create_eval_run(
        db,
        dataset_id=run.dataset_id,
        persona_id=run.persona_id,
        model_name=run.model_name,
    )
    return RunResponse(
        id=r.id,
        dataset_id=r.dataset_id,
        status=r.status,
        started_at=r.started_at,
        completed_at=r.completed_at,
        avg_relevance_score=r.avg_relevance_score,
        avg_accuracy_score=r.avg_accuracy_score,
        total_questions=r.total_questions,
        passed_questions=r.passed_questions,
    )


@router.post("/runs/{run_id}/complete", response_model=RunResponse)
def finish_eval_run(
    run_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Complete an eval run and calculate scores"""
    try:
        r = complete_eval_run(db, run_id)
        return RunResponse(
            id=r.id,
            dataset_id=r.dataset_id,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            avg_relevance_score=r.avg_relevance_score,
            avg_accuracy_score=r.avg_accuracy_score,
            total_questions=r.total_questions,
            passed_questions=r.passed_questions,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
