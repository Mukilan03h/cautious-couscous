"""
Analytics Database Operations for MyPlatform.
Ported from ee/esa/db/analytics.py - FULL ENTERPRISE QUALITY
"""
import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import cast
from sqlalchemy import Date
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import Column, DateTime, Integer, String, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from esa.configs.constants import MessageType
from esa.db.models import Base
from esa.db.models import ChatMessage
from esa.db.models import ChatMessageFeedback
from esa.db.models import ChatSession
from esa.db.models import Persona
from esa.db.models import User
from esa.db.models import UserRole


# =============================================================================
# ENTERPRISE ANALYTICS QUERY FUNCTIONS
# =============================================================================


def fetch_query_analytics(
    start: datetime.datetime,
    end: datetime.datetime,
    db_session: Session,
) -> Sequence[tuple[int, int, int, datetime.date]]:
    """
    Fetch query analytics including message counts and feedback.
    Returns: count, positive_feedback, negative_feedback, date
    """
    stmt = (
        select(
            func.count(ChatMessage.id),
            func.sum(case((ChatMessageFeedback.is_positive, 1), else_=0)),
            func.sum(
                case(
                    (ChatMessageFeedback.is_positive == False, 1), else_=0  # noqa: E712
                )
            ),
            cast(ChatMessage.time_sent, Date),
        )
        .join(
            ChatMessageFeedback,
            ChatMessageFeedback.chat_message_id == ChatMessage.id,
            isouter=True,
        )
        .where(
            ChatMessage.time_sent >= start,
        )
        .where(
            ChatMessage.time_sent <= end,
        )
        .where(ChatMessage.message_type == MessageType.ASSISTANT)
        .group_by(cast(ChatMessage.time_sent, Date))
        .order_by(cast(ChatMessage.time_sent, Date))
    )

    return db_session.execute(stmt).all()  # type: ignore


def fetch_per_user_query_analytics(
    start: datetime.datetime,
    end: datetime.datetime,
    db_session: Session,
) -> Sequence[tuple[int, int, int, datetime.date, UUID]]:
    """
    Fetch per-user query analytics.
    Returns: count, positive_feedback, negative_feedback, date, user_id
    """
    stmt = (
        select(
            func.count(ChatMessage.id),
            func.sum(case((ChatMessageFeedback.is_positive, 1), else_=0)),
            func.sum(
                case(
                    (ChatMessageFeedback.is_positive == False, 1), else_=0  # noqa: E712
                )
            ),
            cast(ChatMessage.time_sent, Date),
            ChatSession.user_id,
        )
        .join(ChatSession, ChatSession.id == ChatMessage.chat_session_id)
        .join(
            ChatMessageFeedback,
            ChatMessageFeedback.chat_message_id == ChatMessage.id,
            isouter=True,
        )
        .where(
            ChatMessage.time_sent >= start,
        )
        .where(
            ChatMessage.time_sent <= end,
        )
        .where(ChatMessage.message_type == MessageType.ASSISTANT)
        .group_by(cast(ChatMessage.time_sent, Date), ChatSession.user_id)
        .order_by(cast(ChatMessage.time_sent, Date), ChatSession.user_id)
    )

    return db_session.execute(stmt).all()  # type: ignore


def fetch_esabot_analytics(
    start: datetime.datetime,
    end: datetime.datetime,
    db_session: Session,
) -> Sequence[tuple[int, int, datetime.date]]:
    """Gets the:
    Date of each set of aggregated statistics
    Number of ESABot Queries (Chat Sessions)
    Number of instances of Negative feedback OR Needing additional help
    """
    subquery_first_ai_response = (
        db_session.query(
            ChatMessage.chat_session_id.label("chat_session_id"),
            func.min(ChatMessage.id).label("chat_message_id"),
        )
        .join(ChatSession, ChatSession.id == ChatMessage.chat_session_id)
        .where(
            ChatSession.time_created >= start,
            ChatSession.time_created <= end,
            ChatSession.esabot_flow.is_(True),
        )
        .where(
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
        .group_by(ChatMessage.chat_session_id)
        .subquery()
    )

    subquery_last_feedback = (
        db_session.query(
            ChatMessageFeedback.chat_message_id.label("chat_message_id"),
            func.max(ChatMessageFeedback.id).label("max_feedback_id"),
        )
        .group_by(ChatMessageFeedback.chat_message_id)
        .subquery()
    )

    results = (
        db_session.query(
            func.count(ChatSession.id).label("total_sessions"),
            func.sum(
                case(
                    (
                        or_(
                            ChatMessageFeedback.is_positive.is_(False),
                            ChatMessageFeedback.required_followup.is_(True),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("negative_answer"),
            cast(ChatSession.time_created, Date).label("session_date"),
        )
        .join(
            subquery_first_ai_response,
            ChatSession.id == subquery_first_ai_response.c.chat_session_id,
        )
        .outerjoin(
            subquery_last_feedback,
            subquery_first_ai_response.c.chat_message_id
            == subquery_last_feedback.c.chat_message_id,
        )
        .outerjoin(
            ChatMessageFeedback,
            ChatMessageFeedback.id == subquery_last_feedback.c.max_feedback_id,
        )
        .group_by(cast(ChatSession.time_created, Date))
        .order_by(cast(ChatSession.time_created, Date))
        .all()
    )

    return [tuple(row) for row in results]


def fetch_persona_message_analytics(
    db_session: Session,
    persona_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[tuple[int, datetime.date]]:
    """Gets the daily message counts for a specific persona within the given time range."""
    query = (
        select(
            func.count(ChatMessage.id),
            cast(ChatMessage.time_sent, Date),
        )
        .join(
            ChatSession,
            ChatMessage.chat_session_id == ChatSession.id,
        )
        .where(
            ChatSession.persona_id == persona_id,
            ChatMessage.time_sent >= start,
            ChatMessage.time_sent <= end,
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
        .group_by(cast(ChatMessage.time_sent, Date))
        .order_by(cast(ChatMessage.time_sent, Date))
    )

    return [tuple(row) for row in db_session.execute(query).all()]


def fetch_persona_unique_users(
    db_session: Session,
    persona_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[tuple[int, datetime.date]]:
    """Gets the daily unique user counts for a specific persona within the given time range."""
    query = (
        select(
            func.count(func.distinct(ChatSession.user_id)),
            cast(ChatMessage.time_sent, Date),
        )
        .join(
            ChatSession,
            ChatMessage.chat_session_id == ChatSession.id,
        )
        .where(
            ChatSession.persona_id == persona_id,
            ChatMessage.time_sent >= start,
            ChatMessage.time_sent <= end,
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
        .group_by(cast(ChatMessage.time_sent, Date))
        .order_by(cast(ChatMessage.time_sent, Date))
    )

    return [tuple(row) for row in db_session.execute(query).all()]


def fetch_assistant_message_analytics(
    db_session: Session,
    assistant_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[tuple[int, datetime.date]]:
    """
    Gets the daily message counts for a specific assistant in the given time range.
    """
    query = (
        select(
            func.count(ChatMessage.id),
            cast(ChatMessage.time_sent, Date),
        )
        .join(
            ChatSession,
            ChatMessage.chat_session_id == ChatSession.id,
        )
        .where(
            ChatSession.persona_id == assistant_id,
            ChatMessage.time_sent >= start,
            ChatMessage.time_sent <= end,
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
        .group_by(cast(ChatMessage.time_sent, Date))
        .order_by(cast(ChatMessage.time_sent, Date))
    )

    return [tuple(row) for row in db_session.execute(query).all()]


def fetch_assistant_unique_users(
    db_session: Session,
    assistant_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[tuple[int, datetime.date]]:
    """
    Gets the daily unique user counts for a specific assistant in the given time range.
    """
    query = (
        select(
            func.count(func.distinct(ChatSession.user_id)),
            cast(ChatMessage.time_sent, Date),
        )
        .join(
            ChatSession,
            ChatMessage.chat_session_id == ChatSession.id,
        )
        .where(
            ChatSession.persona_id == assistant_id,
            ChatMessage.time_sent >= start,
            ChatMessage.time_sent <= end,
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
        .group_by(cast(ChatMessage.time_sent, Date))
        .order_by(cast(ChatMessage.time_sent, Date))
    )

    return [tuple(row) for row in db_session.execute(query).all()]


def fetch_assistant_unique_users_total(
    db_session: Session,
    assistant_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> int:
    """
    Gets the total number of distinct users who have sent or received messages from
    the specified assistant in the given time range.
    """
    query = (
        select(func.count(func.distinct(ChatSession.user_id)))
        .select_from(ChatMessage)
        .join(
            ChatSession,
            ChatMessage.chat_session_id == ChatSession.id,
        )
        .where(
            ChatSession.persona_id == assistant_id,
            ChatMessage.time_sent >= start,
            ChatMessage.time_sent <= end,
            ChatMessage.message_type == MessageType.ASSISTANT,
        )
    )

    result = db_session.execute(query).scalar()
    return result if result else 0


def user_can_view_assistant_stats(
    db_session: Session, user: User | None, assistant_id: int
) -> bool:
    """Users can view assistant stats if they created the persona, or if they are an admin"""
    if user is None or user.role == UserRole.ADMIN:
        return True

    stmt = select(Persona).where(
        and_(Persona.id == assistant_id, Persona.user_id == user.id)
    )

    persona = db_session.execute(stmt).scalar_one_or_none()
    return persona is not None


# =============================================================================
# CUSTOM ANALYTICS MODELS
# =============================================================================


class CustomUsageStats(Base):
    """Daily aggregated usage statistics"""
    __tablename__ = "custom_usage_stats"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    
    total_chats = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    
    total_searches = Column(Integer, default=0)
    avg_search_latency_ms = Column(Float, default=0)
    
    total_documents_indexed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CustomUserActivity(Base):
    """Per-user activity tracking for analytics"""
    __tablename__ = "custom_user_activity"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    chat_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    search_count = Column(Integer, default=0)
    document_uploads = Column(Integer, default=0)
    
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
