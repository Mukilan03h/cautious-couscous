"""
Custom Query History API

View and export query history for admin analysis.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.query_history import (
    get_query_history,
    get_query_count,
    get_feedback_summary,
    update_query_feedback,
    CustomQueryLog,
)


router = APIRouter(prefix="/api/admin/query-history", tags=["query-history"])


# ============ Pydantic Models ============

class QueryLogResponse(BaseModel):
    id: int
    user_id: Optional[str]
    query_text: str
    response_text: Optional[str]
    timestamp: datetime
    response_time_ms: Optional[int]
    prompt_tokens: int
    completion_tokens: int
    documents_retrieved: int
    sources_cited: int
    model_name: Optional[str]
    feedback_positive: Optional[bool]
    feedback_text: Optional[str]
    
    class Config:
        from_attributes = True


class QueryHistoryPage(BaseModel):
    queries: List[QueryLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class FeedbackSummary(BaseModel):
    total_queries: int
    positive_feedback: int
    negative_feedback: int
    no_feedback: int
    satisfaction_rate: float


class FeedbackUpdate(BaseModel):
    is_positive: bool
    feedback_text: Optional[str] = None


# ============ Endpoints ============

@router.get("/", response_model=QueryHistoryPage)
def list_query_history(
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=50, ge=1, le=200),
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    has_feedback: Optional[bool] = None,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Get paginated query history"""
    from uuid import UUID
    
    uid = UUID(user_id) if user_id else None
    
    queries = get_query_history(
        db_session=db,
        user_id=uid,
        start_time=start_date,
        end_time=end_date,
        page=page,
        page_size=page_size,
        has_feedback=has_feedback,
    )
    
    total = get_query_count(
        db_session=db,
        user_id=uid,
        start_time=start_date,
        end_time=end_date,
    )
    
    return QueryHistoryPage(
        queries=[
            QueryLogResponse(
                id=q.id,
                user_id=str(q.user_id) if q.user_id else None,
                query_text=q.query_text,
                response_text=q.response_text,
                timestamp=q.timestamp,
                response_time_ms=q.response_time_ms,
                prompt_tokens=q.prompt_tokens,
                completion_tokens=q.completion_tokens,
                documents_retrieved=q.documents_retrieved,
                sources_cited=q.sources_cited,
                model_name=q.model_name,
                feedback_positive=q.feedback_positive,
                feedback_text=q.feedback_text,
            )
            for q in queries
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page + 1) * page_size < total,
    )


@router.get("/feedback-summary", response_model=FeedbackSummary)
def get_feedback_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Get feedback statistics summary"""
    start_time = datetime.utcnow() - timedelta(days=days)
    
    summary = get_feedback_summary(
        db_session=db,
        start_time=start_time,
    )
    
    return FeedbackSummary(**summary)


@router.patch("/{query_id}/feedback")
def update_feedback(
    query_id: int,
    feedback: FeedbackUpdate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Update feedback for a specific query"""
    updated = update_query_feedback(
        db_session=db,
        query_id=query_id,
        is_positive=feedback.is_positive,
        feedback_text=feedback.feedback_text,
    )
    
    if not updated:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Query not found")
    
    return {"status": "updated", "query_id": query_id}


@router.get("/export")
def export_query_history(
    days: int = Query(default=30, ge=1, le=365),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Export query history data"""
    start_time = datetime.utcnow() - timedelta(days=days)
    
    queries = get_query_history(
        db_session=db,
        start_time=start_time,
        page=0,
        page_size=10000,  # Large export limit
    )
    
    data = [
        {
            "timestamp": q.timestamp.isoformat(),
            "query": q.query_text[:200],  # Truncate for export
            "response_time_ms": q.response_time_ms,
            "prompt_tokens": q.prompt_tokens,
            "completion_tokens": q.completion_tokens,
            "feedback": "positive" if q.feedback_positive else ("negative" if q.feedback_positive is False else "none"),
        }
        for q in queries
    ]
    
    if format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=query_history_{days}d.csv"}
        )
    
    return {"period_days": days, "total": len(data), "data": data}
