"""
Custom Standard Answers - Pre-defined answers for common questions
"""
import re
import string
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Table, ForeignKey, select
from sqlalchemy.orm import Session, relationship

from esa.db.models import Base


# Association table for answers <-> categories
standard_answer_category_association = Table(
    "custom_standard_answer_category_assoc",
    Base.metadata,
    Column("answer_id", Integer, ForeignKey("custom_standard_answer.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("custom_standard_answer_category.id"), primary_key=True),
)


class CustomStandardAnswerCategory(Base):
    """Categories for organizing standard answers"""
    __tablename__ = "custom_standard_answer_category"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomStandardAnswer(Base):
    """Pre-defined answers that match keywords or regex patterns"""
    __tablename__ = "custom_standard_answer"
    
    id = Column(Integer, primary_key=True)
    
    # Matching criteria
    keyword = Column(String, nullable=False)  # Keywords or regex pattern
    match_regex = Column(Boolean, default=False)  # If True, keyword is a regex
    match_any_keywords = Column(Boolean, default=True)  # If True, match any keyword; else match all
    
    # The answer content
    answer = Column(Text, nullable=False)
    
    # Status
    active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Categories relationship
    categories = relationship(
        "CustomStandardAnswerCategory",
        secondary=standard_answer_category_association,
        backref="answers"
    )


# ============ CRUD Functions ============

def create_category(db_session: Session, name: str, description: str = None) -> CustomStandardAnswerCategory:
    """Create a new category"""
    if len(name) > 255:
        raise ValueError("Category name too long (max 255 chars)")
    
    category = CustomStandardAnswerCategory(name=name, description=description)
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def get_categories(db_session: Session) -> Sequence[CustomStandardAnswerCategory]:
    """Get all categories"""
    return db_session.scalars(select(CustomStandardAnswerCategory)).all()


def create_standard_answer(
    db_session: Session,
    keyword: str,
    answer: str,
    category_ids: List[int] = None,
    match_regex: bool = False,
    match_any_keywords: bool = True,
) -> CustomStandardAnswer:
    """Create a new standard answer"""
    categories = []
    if category_ids:
        categories = db_session.scalars(
            select(CustomStandardAnswerCategory)
            .where(CustomStandardAnswerCategory.id.in_(category_ids))
        ).all()
    
    std_answer = CustomStandardAnswer(
        keyword=keyword,
        answer=answer,
        match_regex=match_regex,
        match_any_keywords=match_any_keywords,
        categories=list(categories),
    )
    db_session.add(std_answer)
    db_session.commit()
    db_session.refresh(std_answer)
    return std_answer


def get_standard_answers(
    db_session: Session,
    active_only: bool = True,
    category_id: int = None,
) -> Sequence[CustomStandardAnswer]:
    """Get standard answers with optional filtering"""
    stmt = select(CustomStandardAnswer)
    
    if active_only:
        stmt = stmt.where(CustomStandardAnswer.active == True)
    
    if category_id:
        stmt = stmt.join(standard_answer_category_association).where(
            standard_answer_category_association.c.category_id == category_id
        )
    
    return db_session.scalars(stmt).all()


def update_standard_answer(
    db_session: Session,
    answer_id: int,
    keyword: str = None,
    answer: str = None,
    match_regex: bool = None,
    match_any_keywords: bool = None,
    active: bool = None,
    category_ids: List[int] = None,
) -> CustomStandardAnswer:
    """Update a standard answer"""
    std_answer = db_session.get(CustomStandardAnswer, answer_id)
    if not std_answer:
        raise ValueError(f"Standard answer {answer_id} not found")
    
    if keyword is not None:
        std_answer.keyword = keyword
    if answer is not None:
        std_answer.answer = answer
    if match_regex is not None:
        std_answer.match_regex = match_regex
    if match_any_keywords is not None:
        std_answer.match_any_keywords = match_any_keywords
    if active is not None:
        std_answer.active = active
    if category_ids is not None:
        categories = db_session.scalars(
            select(CustomStandardAnswerCategory)
            .where(CustomStandardAnswerCategory.id.in_(category_ids))
        ).all()
        std_answer.categories = list(categories)
    
    db_session.commit()
    db_session.refresh(std_answer)
    return std_answer


def delete_standard_answer(db_session: Session, answer_id: int) -> bool:
    """Soft delete (deactivate) a standard answer"""
    std_answer = db_session.get(CustomStandardAnswer, answer_id)
    if std_answer:
        std_answer.active = False
        db_session.commit()
        return True
    return False


def find_matching_answers(
    db_session: Session,
    query: str,
    category_ids: List[int] = None,
) -> List[tuple]:
    """Find standard answers matching the query"""
    stmt = select(CustomStandardAnswer).where(CustomStandardAnswer.active == True)
    
    if category_ids:
        stmt = stmt.join(standard_answer_category_association).where(
            standard_answer_category_association.c.category_id.in_(category_ids)
        )
    
    answers = db_session.scalars(stmt).all()
    matches = []
    
    for std_answer in answers:
        if std_answer.match_regex:
            # Regex matching
            try:
                match = re.search(std_answer.keyword, query, re.IGNORECASE)
                if match:
                    matches.append((std_answer, match.group(0)))
            except re.error:
                continue
        else:
            # Keyword matching
            keyword_words = set(
                "".join(c for c in std_answer.keyword.lower() if c not in string.punctuation).split()
            )
            query_words = set(
                "".join(c for c in query.lower() if c not in string.punctuation).split()
            )
            
            if std_answer.match_any_keywords:
                # Match any keyword
                if keyword_words & query_words:
                    matches.append((std_answer, ", ".join(keyword_words & query_words)))
            else:
                # Match all keywords
                if keyword_words <= query_words:
                    matches.append((std_answer, ", ".join(keyword_words)))
    
    return matches


# ============ EE-Compatible Function Wrappers ============
# These wrappers provide the same function signatures as EE for API compatibility


def fetch_standard_answer(
    standard_answer_id: int,
    db_session: Session,
) -> CustomStandardAnswer | None:
    """Fetch a single standard answer by ID."""
    return db_session.get(CustomStandardAnswer, standard_answer_id)


def fetch_standard_answers(db_session: Session) -> Sequence[CustomStandardAnswer]:
    """Fetch all standard answers."""
    return get_standard_answers(db_session, active_only=False)


def fetch_standard_answer_category(
    standard_answer_category_id: int,
    db_session: Session,
) -> CustomStandardAnswerCategory | None:
    """Fetch a single category by ID."""
    return db_session.get(CustomStandardAnswerCategory, standard_answer_category_id)


def fetch_standard_answer_categories(
    db_session: Session,
) -> Sequence[CustomStandardAnswerCategory]:
    """Fetch all categories."""
    return get_categories(db_session)


def insert_standard_answer(
    keyword: str,
    answer: str,
    category_ids: list[int],
    match_regex: bool,
    match_any_keywords: bool,
    db_session: Session,
) -> CustomStandardAnswer:
    """Insert a new standard answer (EE-compatible signature)."""
    return create_standard_answer(
        db_session=db_session,
        keyword=keyword,
        answer=answer,
        category_ids=category_ids,
        match_regex=match_regex,
        match_any_keywords=match_any_keywords,
    )


def insert_standard_answer_category(
    category_name: str,
    db_session: Session,
) -> CustomStandardAnswerCategory:
    """Insert a new category (EE-compatible signature)."""
    return create_category(db_session=db_session, name=category_name)


def remove_standard_answer(
    standard_answer_id: int,
    db_session: Session,
) -> None:
    """Remove a standard answer (EE-compatible signature)."""
    std_answer = db_session.get(CustomStandardAnswer, standard_answer_id)
    if std_answer:
        db_session.delete(std_answer)
        db_session.commit()


def update_standard_answer_category(
    standard_answer_category_id: int,
    category_name: str,
    db_session: Session,
) -> CustomStandardAnswerCategory:
    """Update a category (EE-compatible signature)."""
    category = db_session.get(CustomStandardAnswerCategory, standard_answer_category_id)
    if not category:
        raise ValueError(f"Category {standard_answer_category_id} not found")
    category.name = category_name
    db_session.commit()
    db_session.refresh(category)
    return category


def find_matching_standard_answers(
    id_in: list[int],
    query: str,
    db_session: Session,
) -> list[tuple]:
    """Find matching standard answers (EE-compatible signature)."""
    return find_matching_answers(db_session=db_session, query=query, category_ids=id_in)

