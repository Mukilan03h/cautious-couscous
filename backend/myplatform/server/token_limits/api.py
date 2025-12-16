"""
Custom Token Rate Limits API

Configure and monitor token usage limits.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user, current_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.token_limits import (
    create_token_limit,
    get_token_limits,
    get_user_applicable_limits,
    update_token_limit,
    delete_token_limit,
    check_token_limit,
    record_token_usage,
    CustomTokenLimit,
)


router = APIRouter(prefix="/api/admin/token-limits", tags=["token-limits"])
user_router = APIRouter(prefix="/api/token-usage", tags=["token-usage"])


# ============ Pydantic Models ============

class TokenLimitCreate(BaseModel):
    token_budget: int
    period_hours: int = 24
    scope: str = "global"  # global, group, user
    target_user_id: Optional[str] = None
    target_group_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TokenLimitUpdate(BaseModel):
    enabled: Optional[bool] = None
    token_budget: Optional[int] = None
    period_hours: Optional[int] = None


class TokenLimitResponse(BaseModel):
    id: int
    scope: str
    target_user_id: Optional[str]
    target_group_id: Optional[int]
    enabled: bool
    token_budget: int
    period_hours: int
    name: Optional[str]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenUsageStatus(BaseModel):
    allowed: bool
    total_used: int
    budget: int
    remaining: int
    period_hours: int
    period_ends: Optional[str]
    limit_name: Optional[str]


class RecordUsageRequest(BaseModel):
    prompt_tokens: int
    completion_tokens: int


# ============ Admin Endpoints ============

@router.get("/", response_model=List[TokenLimitResponse])
def list_token_limits(
    scope: Optional[str] = None,
    include_disabled: bool = False,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List all token limits"""
    limits = get_token_limits(
        db_session=db,
        scope=scope,
        enabled_only=not include_disabled,
    )
    
    return [
        TokenLimitResponse(
            id=l.id,
            scope=l.scope,
            target_user_id=str(l.target_user_id) if l.target_user_id else None,
            target_group_id=l.target_group_id,
            enabled=l.enabled,
            token_budget=l.token_budget,
            period_hours=l.period_hours,
            name=l.name,
            description=l.description,
            created_at=l.created_at,
        )
        for l in limits
    ]


@router.post("/", response_model=TokenLimitResponse)
def create_new_token_limit(
    limit: TokenLimitCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new token limit"""
    target_uid = UUID(limit.target_user_id) if limit.target_user_id else None
    
    new_limit = create_token_limit(
        db_session=db,
        token_budget=limit.token_budget,
        period_hours=limit.period_hours,
        scope=limit.scope,
        target_user_id=target_uid,
        target_group_id=limit.target_group_id,
        name=limit.name,
        description=limit.description,
    )
    
    return TokenLimitResponse(
        id=new_limit.id,
        scope=new_limit.scope,
        target_user_id=str(new_limit.target_user_id) if new_limit.target_user_id else None,
        target_group_id=new_limit.target_group_id,
        enabled=new_limit.enabled,
        token_budget=new_limit.token_budget,
        period_hours=new_limit.period_hours,
        name=new_limit.name,
        description=new_limit.description,
        created_at=new_limit.created_at,
    )


@router.patch("/{limit_id}", response_model=TokenLimitResponse)
def update_existing_limit(
    limit_id: int,
    update: TokenLimitUpdate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Update a token limit"""
    updated = update_token_limit(
        db_session=db,
        limit_id=limit_id,
        enabled=update.enabled,
        token_budget=update.token_budget,
        period_hours=update.period_hours,
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Token limit not found")
    
    return TokenLimitResponse(
        id=updated.id,
        scope=updated.scope,
        target_user_id=str(updated.target_user_id) if updated.target_user_id else None,
        target_group_id=updated.target_group_id,
        enabled=updated.enabled,
        token_budget=updated.token_budget,
        period_hours=updated.period_hours,
        name=updated.name,
        description=updated.description,
        created_at=updated.created_at,
    )


@router.delete("/{limit_id}")
def delete_existing_limit(
    limit_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Delete a token limit"""
    deleted = delete_token_limit(db, limit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Token limit not found")
    return {"status": "deleted", "limit_id": limit_id}


# ============ User Endpoints ============

@user_router.get("/status", response_model=TokenUsageStatus)
def get_my_token_status(
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Get current user's token usage status"""
    # Get user's groups for group-based limits
    group_ids = []
    if hasattr(user, 'custom_groups'):
        group_ids = [g.id for g in user.custom_groups]
    
    status = check_token_limit(
        db_session=db,
        user_id=user.id,
        group_ids=group_ids if group_ids else None,
    )
    
    return TokenUsageStatus(
        allowed=status.get("allowed", True),
        total_used=status.get("total_used", 0),
        budget=status.get("budget", 0),
        remaining=status.get("remaining", 0),
        period_hours=status.get("period_hours", 24),
        period_ends=status.get("period_ends"),
        limit_name=status.get("limit_name"),
    )


@user_router.post("/record")
def record_my_usage(
    usage: RecordUsageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Record token usage (called internally by chat)"""
    record = record_token_usage(
        db_session=db,
        user_id=user.id,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    
    return {
        "recorded": True,
        "total_prompt_tokens": record.prompt_tokens,
        "total_completion_tokens": record.completion_tokens,
    }
