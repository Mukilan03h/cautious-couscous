"""
Custom Token Rate Limits Database Models and Functions
"""
from datetime import datetime, timedelta
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float, ForeignKey, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session, relationship

from esa.db.models import Base


class CustomTokenLimit(Base):
    """
    Token rate limit configuration.
    Can be applied globally, per-group, or per-user.
    """
    __tablename__ = "custom_token_limit"
    
    id = Column(Integer, primary_key=True)
    
    # Scope: 'global', 'group', 'user'
    scope = Column(String, nullable=False, default='global', index=True)
    
    # Target (user_id or group_id, null for global)
    target_user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    target_group_id = Column(Integer, ForeignKey("user_group.id"), nullable=True, index=True)
    
    # Limit settings
    enabled = Column(Boolean, default=True)
    token_budget = Column(Integer, nullable=False)  # Max tokens allowed
    period_hours = Column(Integer, nullable=False, default=24)  # Reset period
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Description
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)


class CustomTokenUsage(Base):
    """
    Track actual token usage per user for rate limiting.
    """
    __tablename__ = "custom_token_usage"
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Usage tracking
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    # Period tracking
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Last update
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ Token Limit CRUD ============

def create_token_limit(
    db_session: Session,
    token_budget: int,
    period_hours: int = 24,
    scope: str = 'global',
    target_user_id: UUID | None = None,
    target_group_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
) -> CustomTokenLimit:
    """Create a new token limit"""
    limit = CustomTokenLimit(
        scope=scope,
        target_user_id=target_user_id,
        target_group_id=target_group_id,
        token_budget=token_budget,
        period_hours=period_hours,
        name=name,
        description=description,
    )
    db_session.add(limit)
    db_session.commit()
    db_session.refresh(limit)
    return limit


def get_token_limits(
    db_session: Session,
    scope: str | None = None,
    enabled_only: bool = True,
) -> Sequence[CustomTokenLimit]:
    """Get all token limits, optionally filtered by scope"""
    stmt = select(CustomTokenLimit)
    
    if scope:
        stmt = stmt.where(CustomTokenLimit.scope == scope)
    if enabled_only:
        stmt = stmt.where(CustomTokenLimit.enabled == True)
    
    stmt = stmt.order_by(CustomTokenLimit.created_at.desc())
    return db_session.scalars(stmt).all()


def get_user_applicable_limits(
    db_session: Session,
    user_id: UUID,
    group_ids: list[int] | None = None,
) -> Sequence[CustomTokenLimit]:
    """Get all token limits that apply to a user"""
    stmt = select(CustomTokenLimit).where(CustomTokenLimit.enabled == True)
    
    conditions = [
        CustomTokenLimit.scope == 'global',
        CustomTokenLimit.target_user_id == user_id,
    ]
    
    if group_ids:
        conditions.append(CustomTokenLimit.target_group_id.in_(group_ids))
    
    from sqlalchemy import or_
    stmt = stmt.where(or_(*conditions))
    
    return db_session.scalars(stmt).all()


def update_token_limit(
    db_session: Session,
    limit_id: int,
    enabled: bool | None = None,
    token_budget: int | None = None,
    period_hours: int | None = None,
) -> CustomTokenLimit | None:
    """Update a token limit"""
    limit = db_session.get(CustomTokenLimit, limit_id)
    if limit:
        if enabled is not None:
            limit.enabled = enabled
        if token_budget is not None:
            limit.token_budget = token_budget
        if period_hours is not None:
            limit.period_hours = period_hours
        db_session.commit()
        db_session.refresh(limit)
    return limit


def delete_token_limit(db_session: Session, limit_id: int) -> bool:
    """Delete a token limit"""
    limit = db_session.get(CustomTokenLimit, limit_id)
    if limit:
        db_session.delete(limit)
        db_session.commit()
        return True
    return False


# ============ Token Usage Tracking ============

def get_or_create_usage_record(
    db_session: Session,
    user_id: UUID,
    period_hours: int = 24,
) -> CustomTokenUsage:
    """Get current usage record or create new one if period expired"""
    now = datetime.utcnow()
    period_start = now - timedelta(hours=period_hours)
    
    # Find current period usage
    stmt = select(CustomTokenUsage).where(
        CustomTokenUsage.user_id == user_id,
        CustomTokenUsage.period_end > now,
    )
    usage = db_session.scalar(stmt)
    
    if not usage:
        # Create new usage record
        usage = CustomTokenUsage(
            user_id=user_id,
            period_start=now,
            period_end=now + timedelta(hours=period_hours),
            prompt_tokens=0,
            completion_tokens=0,
        )
        db_session.add(usage)
        db_session.commit()
        db_session.refresh(usage)
    
    return usage


def record_token_usage(
    db_session: Session,
    user_id: UUID,
    prompt_tokens: int,
    completion_tokens: int,
    period_hours: int = 24,
) -> CustomTokenUsage:
    """Record token usage for a user"""
    usage = get_or_create_usage_record(db_session, user_id, period_hours)
    usage.prompt_tokens += prompt_tokens
    usage.completion_tokens += completion_tokens
    db_session.commit()
    db_session.refresh(usage)
    return usage


def check_token_limit(
    db_session: Session,
    user_id: UUID,
    group_ids: list[int] | None = None,
) -> dict:
    """Check if user is within token limits"""
    limits = get_user_applicable_limits(db_session, user_id, group_ids)
    
    if not limits:
        return {
            "allowed": True,
            "reason": "No limits configured",
            "limits": [],
        }
    
    # Get strictest limit
    strictest = min(limits, key=lambda l: l.token_budget)
    
    # Get current usage
    usage = get_or_create_usage_record(db_session, user_id, strictest.period_hours)
    total_used = usage.prompt_tokens + usage.completion_tokens
    
    allowed = total_used < strictest.token_budget
    remaining = max(0, strictest.token_budget - total_used)
    
    return {
        "allowed": allowed,
        "total_used": total_used,
        "budget": strictest.token_budget,
        "remaining": remaining,
        "period_hours": strictest.period_hours,
        "period_ends": usage.period_end.isoformat() if usage else None,
        "limit_name": strictest.name,
    }
