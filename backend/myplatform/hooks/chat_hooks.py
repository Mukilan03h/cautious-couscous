"""
Chat Integration Hooks - Query Logging and Token Tracking

These hooks integrate with ESA's chat system to:
1. Log all queries to custom_query_log
2. Track token usage per user
3. Check rate limits before LLM calls
4. Check for matching standard answers
"""
import time
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from myplatform.db.query_history import log_query, CustomQueryLog
from myplatform.db.token_limits import (
    record_token_usage,
    check_token_limit,
    get_or_create_usage_record,
)
from myplatform.db.standard_answers import find_matching_answers
from esa.utils.logger import setup_logger

logger = setup_logger()


class ChatHooks:
    """Hooks into ESA chat flow for enterprise features"""
    
    @staticmethod
    def before_llm_call(
        db_session: Session,
        user_id: UUID,
        query_text: str,
        chat_session_id: int = None,
        group_ids: list[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Called before making an LLM call.
        
        Returns:
            (can_proceed, standard_answer, rate_limit_info)
            - can_proceed: False if rate limited
            - standard_answer: If matches a standard answer, return it instead of LLM
            - rate_limit_info: Token usage status
        """
        # Check for standard answers first
        matches = find_matching_answers(db_session, query_text)
        if matches:
            best_match, matched_text = matches[0]
            logger.info(f"Standard answer match: {matched_text}")
            return True, best_match.answer, None
        
        # Check rate limits
        limit_status = check_token_limit(db_session, user_id, group_ids)
        if not limit_status.get("allowed", True):
            logger.warning(f"User {user_id} rate limited: {limit_status}")
            return False, None, limit_status
        
        return True, None, limit_status
    
    @staticmethod
    def after_llm_call(
        db_session: Session,
        user_id: UUID,
        query_text: str,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        chat_session_id: int = None,
        model_name: str = None,
        documents_retrieved: int = 0,
        sources_cited: int = 0,
        response_time_ms: int = None,
    ) -> CustomQueryLog:
        """
        Called after LLM response is generated.
        Logs query and tracks token usage.
        """
        # Log the query
        query_log = log_query(
            db_session=db_session,
            query_text=query_text,
            user_id=user_id,
            chat_session_id=chat_session_id,
            response_text=response_text,
            response_time_ms=response_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            documents_retrieved=documents_retrieved,
            sources_cited=sources_cited,
            model_name=model_name,
        )
        
        # Track token usage
        record_token_usage(
            db_session=db_session,
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        
        logger.debug(
            f"Logged query {query_log.id}: {prompt_tokens}+{completion_tokens} tokens"
        )
        
        return query_log


class QueryTimer:
    """Context manager for timing query execution"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
    
    @property
    def elapsed_ms(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0


# Convenience functions for direct import
def check_before_chat(
    db_session: Session,
    user_id: UUID,
    query: str,
    group_ids: list[int] = None,
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Check rate limits and standard answers before chat"""
    return ChatHooks.before_llm_call(db_session, user_id, query, group_ids=group_ids)


def log_after_chat(
    db_session: Session,
    user_id: UUID,
    query: str,
    response: str,
    prompt_tokens: int,
    completion_tokens: int,
    **kwargs,
) -> CustomQueryLog:
    """Log query and track tokens after chat"""
    return ChatHooks.after_llm_call(
        db_session=db_session,
        user_id=user_id,
        query_text=query,
        response_text=response,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        **kwargs,
    )
