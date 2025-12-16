"""
Analytics Recording - Track usage automatically
"""
from datetime import datetime, date
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from myplatform.db.analytics import CustomUsageStats, CustomUserActivity
from esa.utils.logger import setup_logger

logger = setup_logger()


def record_user_activity(
    db_session: Session,
    user_id: UUID,
    chat_count: int = 0,
    message_count: int = 0,
    search_count: int = 0,
    document_uploads: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> CustomUserActivity:
    """Record or update user activity for today"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find existing record for today
    stmt = select(CustomUserActivity).where(
        CustomUserActivity.user_id == user_id,
        CustomUserActivity.date == today,
    )
    activity = db_session.scalar(stmt)
    
    if activity:
        # Update existing
        activity.chat_count += chat_count
        activity.message_count += message_count
        activity.search_count += search_count
        activity.document_uploads += document_uploads
        activity.prompt_tokens += prompt_tokens
        activity.completion_tokens += completion_tokens
    else:
        # Create new
        activity = CustomUserActivity(
            user_id=user_id,
            date=today,
            chat_count=chat_count,
            message_count=message_count,
            search_count=search_count,
            document_uploads=document_uploads,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        db_session.add(activity)
    
    db_session.commit()
    return activity


def update_daily_stats(
    db_session: Session,
    chat_count: int = 0,
    message_count: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    search_count: int = 0,
    documents_indexed: int = 0,
) -> CustomUsageStats:
    """Update aggregated daily stats"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stmt = select(CustomUsageStats).where(CustomUsageStats.date == today)
    stats = db_session.scalar(stmt)
    
    if stats:
        stats.total_chats += chat_count
        stats.total_messages += message_count
        stats.total_prompt_tokens += prompt_tokens
        stats.total_completion_tokens += completion_tokens
        stats.total_searches += search_count
        stats.total_documents_indexed += documents_indexed
    else:
        # Count unique users for today
        unique_users = db_session.scalar(
            select(func.count(func.distinct(CustomUserActivity.user_id))).where(
                CustomUserActivity.date == today
            )
        ) or 0
        
        stats = CustomUsageStats(
            date=today,
            total_chats=chat_count,
            total_messages=message_count,
            unique_users=unique_users,
            total_prompt_tokens=prompt_tokens,
            total_completion_tokens=completion_tokens,
            total_searches=search_count,
            total_documents_indexed=documents_indexed,
        )
        db_session.add(stats)
    
    db_session.commit()
    return stats
