"""
Custom Standard Answers API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.standard_answers import (
    create_category,
    get_categories,
    create_standard_answer,
    get_standard_answers,
    update_standard_answer,
    delete_standard_answer,
    find_matching_answers,
    CustomStandardAnswer,
    CustomStandardAnswerCategory,
)


router = APIRouter(prefix="/api/admin/standard-answers", tags=["standard-answers"])


# ============ Pydantic Models ============

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True


class AnswerCreate(BaseModel):
    keyword: str
    answer: str
    category_ids: List[int] = []
    match_regex: bool = False
    match_any_keywords: bool = True


class AnswerUpdate(BaseModel):
    keyword: Optional[str] = None
    answer: Optional[str] = None
    category_ids: Optional[List[int]] = None
    match_regex: Optional[bool] = None
    match_any_keywords: Optional[bool] = None
    active: Optional[bool] = None


class AnswerResponse(BaseModel):
    id: int
    keyword: str
    answer: str
    match_regex: bool
    match_any_keywords: bool
    active: bool
    category_ids: List[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MatchQuery(BaseModel):
    query: str
    category_ids: Optional[List[int]] = None


class MatchResult(BaseModel):
    answer_id: int
    keyword: str
    answer: str
    matched_text: str


# ============ Category Endpoints ============

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List all categories"""
    return [
        CategoryResponse(id=c.id, name=c.name, description=c.description)
        for c in get_categories(db)
    ]


@router.post("/categories", response_model=CategoryResponse)
def add_category(
    category: CategoryCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new category"""
    c = create_category(db, category.name, category.description)
    return CategoryResponse(id=c.id, name=c.name, description=c.description)


# ============ Answer Endpoints ============

@router.get("/", response_model=List[AnswerResponse])
def list_answers(
    active_only: bool = True,
    category_id: Optional[int] = None,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List all standard answers"""
    answers = get_standard_answers(db, active_only=active_only, category_id=category_id)
    return [
        AnswerResponse(
            id=a.id,
            keyword=a.keyword,
            answer=a.answer,
            match_regex=a.match_regex,
            match_any_keywords=a.match_any_keywords,
            active=a.active,
            category_ids=[c.id for c in a.categories],
            created_at=a.created_at,
        )
        for a in answers
    ]


@router.post("/", response_model=AnswerResponse)
def add_answer(
    answer: AnswerCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new standard answer"""
    a = create_standard_answer(
        db,
        keyword=answer.keyword,
        answer=answer.answer,
        category_ids=answer.category_ids,
        match_regex=answer.match_regex,
        match_any_keywords=answer.match_any_keywords,
    )
    return AnswerResponse(
        id=a.id,
        keyword=a.keyword,
        answer=a.answer,
        match_regex=a.match_regex,
        match_any_keywords=a.match_any_keywords,
        active=a.active,
        category_ids=[c.id for c in a.categories],
        created_at=a.created_at,
    )


@router.patch("/{answer_id}", response_model=AnswerResponse)
def modify_answer(
    answer_id: int,
    update: AnswerUpdate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Update a standard answer"""
    try:
        a = update_standard_answer(
            db,
            answer_id=answer_id,
            keyword=update.keyword,
            answer=update.answer,
            match_regex=update.match_regex,
            match_any_keywords=update.match_any_keywords,
            active=update.active,
            category_ids=update.category_ids,
        )
        return AnswerResponse(
            id=a.id,
            keyword=a.keyword,
            answer=a.answer,
            match_regex=a.match_regex,
            match_any_keywords=a.match_any_keywords,
            active=a.active,
            category_ids=[c.id for c in a.categories],
            created_at=a.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{answer_id}")
def remove_answer(
    answer_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Delete a standard answer"""
    if delete_standard_answer(db, answer_id):
        return {"status": "deleted", "answer_id": answer_id}
    raise HTTPException(status_code=404, detail="Answer not found")


# ============ Match Endpoint ============

@router.post("/match", response_model=List[MatchResult])
def match_query(
    query: MatchQuery,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Find standard answers matching a query"""
    matches = find_matching_answers(db, query.query, query.category_ids)
    return [
        MatchResult(
            answer_id=answer.id,
            keyword=answer.keyword,
            answer=answer.answer,
            matched_text=matched_text,
        )
        for answer, matched_text in matches
    ]
