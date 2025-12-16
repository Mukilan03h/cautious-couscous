"""
Chat backend models for MyPlatform.
Ported from ee/esa/server/query_and_chat/models.py
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TokenUsageInfo(BaseModel):
    """Information about a user's token usage."""
    has_limit: bool
    limit: Optional[int]
    usage: int
    remaining: Optional[int]
    period: Optional[str]
    period_start: Optional[datetime]


class CheckTokenLimitRequest(BaseModel):
    """Request to check if tokens can be used."""
    user_id: str
    requested_tokens: int


class CheckTokenLimitResponse(BaseModel):
    """Response for token limit check."""
    allowed: bool
    message: Optional[str]
    usage_info: TokenUsageInfo


class ChatWithLimitRequest(BaseModel):
    """Chat request with token limit enforcement."""
    message: str
    persona_id: Optional[int]
    chat_session_id: Optional[int]
    prompt_override: Optional[str]
    retrieval_options: Optional[dict]
    
    # Token limit options
    enforce_token_limit: bool = True
    max_tokens: Optional[int]


class ChatWithLimitResponse(BaseModel):
    """Chat response with token usage info."""
    response: str
    chat_session_id: int
    message_id: int
    tokens_used: int
    usage_info: Optional[TokenUsageInfo]


class QueryBackendRequest(BaseModel):
    """Query request for backend."""
    query: str
    filters: Optional[dict]
    top_k: int = 10
    
    # Permission filtering
    apply_permissions: bool = True
    user_group_ids: Optional[list[int]]
    
    # Token limit options
    enforce_token_limit: bool = True


class QueryBackendResponse(BaseModel):
    """Query response from backend."""
    documents: list[dict]
    processing_time_ms: float
    total_found: int
    tokens_used: int
