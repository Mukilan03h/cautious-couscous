"""
Custom Query History Database Models and Functions
"""
from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Float, asc, desc, func, select, distinct
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Session, joinedload

from esa.db.models import Base, ChatSession, ChatMessage, User


class CustomQueryLog(Base):
    """
    Log of all queries made by users.
    Captures query text, response metadata, and feedback.
    """
    __tablename__ = "custom_query_log"
    
    id = Column(Integer, primary_key=True)
    
    # User and session
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    chat_session_id = Column(Integer, nullable=True, index=True)
    
    # Query details
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    # Search metadata
    documents_retrieved = Column(Integer, default=0)
    sources_cited = Column(Integer, default=0)
    
    # Model info
    model_name = Column(String, nullable=True)
    
    # Feedback
    feedback_positive = Column(Boolean, nullable=True)
    feedback_text = Column(Text, nullable=True)
    
    # Additional metadata as JSON
    extra_metadata = Column(JSONB, nullable=True)


# ============ Query Functions ============

def log_query(
    db_session: Session,
    query_text: str,
    user_id: UUID | None = None,
    chat_session_id: int | None = None,
    response_text: str | None = None,
    response_time_ms: int | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    documents_retrieved: int = 0,
    sources_cited: int = 0,
    model_name: str | None = None,
    extra_metadata: dict | None = None,
) -> CustomQueryLog:
    """Log a new query to the history"""
    log_entry = CustomQueryLog(
        user_id=user_id,
        chat_session_id=chat_session_id,
        query_text=query_text,
        response_text=response_text,
        response_time_ms=response_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        documents_retrieved=documents_retrieved,
        sources_cited=sources_cited,
        model_name=model_name,
        extra_metadata=extra_metadata,
    )
    db_session.add(log_entry)
    db_session.commit()
    return log_entry


def get_query_history(
    db_session: Session,
    user_id: UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 0,
    page_size: int = 50,
    has_feedback: bool | None = None,
) -> Sequence[CustomQueryLog]:
    """Get paginated query history with filters"""
    stmt = select(CustomQueryLog)
    
    if user_id:
        stmt = stmt.where(CustomQueryLog.user_id == user_id)
    if start_time:
        stmt = stmt.where(CustomQueryLog.timestamp >= start_time)
    if end_time:
        stmt = stmt.where(CustomQueryLog.timestamp <= end_time)
    if has_feedback is not None:
        if has_feedback:
            stmt = stmt.where(CustomQueryLog.feedback_positive.isnot(None))
        else:
            stmt = stmt.where(CustomQueryLog.feedback_positive.is_(None))
    
    stmt = stmt.order_by(desc(CustomQueryLog.timestamp))
    stmt = stmt.offset(page * page_size).limit(page_size)
    
    return db_session.scalars(stmt).all()


def get_query_count(
    db_session: Session,
    user_id: UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> int:
    """Get total count of queries matching filters"""
    stmt = select(func.count(CustomQueryLog.id))
    
    if user_id:
        stmt = stmt.where(CustomQueryLog.user_id == user_id)
    if start_time:
        stmt = stmt.where(CustomQueryLog.timestamp >= start_time)
    if end_time:
        stmt = stmt.where(CustomQueryLog.timestamp <= end_time)
    
    return db_session.scalar(stmt) or 0


def update_query_feedback(
    db_session: Session,
    query_id: int,
    is_positive: bool,
    feedback_text: str | None = None,
) -> CustomQueryLog | None:
    """Update feedback for a query"""
    log_entry = db_session.get(CustomQueryLog, query_id)
    if log_entry:
        log_entry.feedback_positive = is_positive
        log_entry.feedback_text = feedback_text
        db_session.commit()
    return log_entry


def get_feedback_summary(
    db_session: Session,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    """Get summary of feedback stats"""
    base_query = select(CustomQueryLog)
    
    if start_time:
        base_query = base_query.where(CustomQueryLog.timestamp >= start_time)
    if end_time:
        base_query = base_query.where(CustomQueryLog.timestamp <= end_time)
    
    total = db_session.scalar(
        select(func.count(CustomQueryLog.id)).select_from(base_query.subquery())
    ) or 0
    
    positive = db_session.scalar(
        select(func.count(CustomQueryLog.id))
        .where(CustomQueryLog.feedback_positive == True)
        .where(CustomQueryLog.timestamp >= start_time if start_time else True)
        .where(CustomQueryLog.timestamp <= end_time if end_time else True)
    ) or 0
    
    negative = db_session.scalar(
        select(func.count(CustomQueryLog.id))
        .where(CustomQueryLog.feedback_positive == False)
        .where(CustomQueryLog.timestamp >= start_time if start_time else True)
        .where(CustomQueryLog.timestamp <= end_time if end_time else True)
    ) or 0
    
    return {
        "total_queries": total,
        "positive_feedback": positive,
        "negative_feedback": negative,
        "no_feedback": total - positive - negative,
        "satisfaction_rate": round(positive / max(positive + negative, 1) * 100, 1)
    }
