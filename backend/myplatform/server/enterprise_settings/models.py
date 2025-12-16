"""
Enterprise settings models for MyPlatform.
Ported from ee/esa/server/enterprise_settings/models.py
"""
from pydantic import BaseModel


class EnterpriseSettings(BaseModel):
    """Enterprise-level settings configuration."""
    
    # Branding
    application_name: str | None = None
    custom_logo: bool = False
    custom_logotype: bool = False
    
    # Feature toggles
    enable_chat_history: bool = True
    enable_feedback: bool = True
    enable_usage_analytics: bool = True
    enable_sharing: bool = True
    
    # Security settings
    require_email_verification: bool = False
    allowed_email_domains: list[str] = []
    
    # Rate limiting
    max_tokens_per_day: int | None = None
    max_messages_per_day: int | None = None
    
    # Custom footer/headers
    custom_header_html: str | None = None
    custom_footer_html: str | None = None
    
    class Config:
        extra = "ignore"


class AnalyticsScriptUpload(BaseModel):
    """Model for uploading custom analytics scripts."""
    script: str
    
    class Config:
        extra = "ignore"
