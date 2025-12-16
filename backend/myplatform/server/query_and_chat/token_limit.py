"""
Token limit handling for chat backend.
Ported from ee/esa/server/query_and_chat/token_limit.py
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from myplatform.db.token_limits import (
    get_token_limit_for_user,
    get_token_limit_for_group,
    get_global_token_limit,
    get_user_token_usage,
)
from esa.db.models import User
from esa.utils.logger import setup_logger

logger = setup_logger()


class TokenLimitExceeded(Exception):
    """Exception raised when a user exceeds their token limit."""
    
    def __init__(self, message: str, limit: int, usage: int, period: str):
        self.message = message
        self.limit = limit
        self.usage = usage
        self.period = period
        super().__init__(self.message)


class TokenLimitChecker:
    """
    Checks and enforces token limits for users.
    
    Token limits can be set at three levels:
    1. User-specific limits
    2. Group-specific limits
    3. Global limits
    
    The most restrictive limit applies.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def check_limit(
        self,
        user: User,
        requested_tokens: int,
    ) -> None:
        """
        Check if a user can use the requested number of tokens.
        
        Args:
            user: The user requesting tokens
            requested_tokens: Number of tokens requested
            
        Raises:
            TokenLimitExceeded: If the user has exceeded their limit
        """
        # Get applicable limits
        user_limit = get_token_limit_for_user(self.db_session, user.id)
        group_limit = self._get_group_limit(user)
        global_limit = get_global_token_limit(self.db_session)
        
        # Get the most restrictive limit
        effective_limit = self._get_effective_limit(user_limit, group_limit, global_limit)
        
        if effective_limit is None:
            return  # No limit set
        
        # Get current usage
        period_start = self._get_period_start(effective_limit.period)
        current_usage = get_user_token_usage(
            self.db_session,
            user.id,
            period_start,
        )
        
        # Check if limit would be exceeded
        if current_usage + requested_tokens > effective_limit.token_budget:
            raise TokenLimitExceeded(
                message=f"Token limit exceeded. Limit: {effective_limit.token_budget}, "
                        f"Usage: {current_usage}, Requested: {requested_tokens}",
                limit=effective_limit.token_budget,
                usage=current_usage,
                period=effective_limit.period,
            )
    
    def _get_group_limit(self, user: User) -> Optional[any]:
        """Get the most restrictive group limit for a user."""
        if not user.groups:
            return None
        
        most_restrictive = None
        for group in user.groups:
            limit = get_token_limit_for_group(self.db_session, group.id)
            if limit:
                if most_restrictive is None or limit.token_budget < most_restrictive.token_budget:
                    most_restrictive = limit
        
        return most_restrictive
    
    def _get_effective_limit(self, *limits) -> Optional[any]:
        """Get the most restrictive limit from a list of limits."""
        valid_limits = [l for l in limits if l is not None]
        if not valid_limits:
            return None
        return min(valid_limits, key=lambda l: l.token_budget)
    
    def _get_period_start(self, period: str) -> datetime:
        """Get the start of the current period."""
        now = datetime.utcnow()
        
        if period == "daily":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == "monthly":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to daily
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_usage_summary(self, user: User) -> dict:
        """
        Get a summary of the user's token usage.
        
        Returns:
            Dict with usage information
        """
        user_limit = get_token_limit_for_user(self.db_session, user.id)
        group_limit = self._get_group_limit(user)
        global_limit = get_global_token_limit(self.db_session)
        effective_limit = self._get_effective_limit(user_limit, group_limit, global_limit)
        
        if effective_limit is None:
            return {
                "has_limit": False,
                "limit": None,
                "usage": 0,
                "remaining": None,
                "period": None,
            }
        
        period_start = self._get_period_start(effective_limit.period)
        current_usage = get_user_token_usage(self.db_session, user.id, period_start)
        
        return {
            "has_limit": True,
            "limit": effective_limit.token_budget,
            "usage": current_usage,
            "remaining": max(0, effective_limit.token_budget - current_usage),
            "period": effective_limit.period,
        }


def check_token_limit(
    db_session: Session,
    user: User,
    requested_tokens: int,
) -> None:
    """
    Convenience function to check token limit.
    
    Args:
        db_session: Database session
        user: The user requesting tokens
        requested_tokens: Number of tokens requested
        
    Raises:
        TokenLimitExceeded: If the user has exceeded their limit
    """
    checker = TokenLimitChecker(db_session)
    checker.check_limit(user, requested_tokens)
