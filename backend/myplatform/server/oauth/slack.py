"""
Slack OAuth implementation for MyPlatform.
"""
import json
from urllib.parse import urlencode

from esa.configs.app_configs import WEB_DOMAIN
from esa.utils.logger import setup_logger

logger = setup_logger()

# Slack OAuth configuration
SLACK_CLIENT_ID = ""  # Set via environment
SLACK_CLIENT_SECRET = ""  # Set via environment
SLACK_OAUTH_SCOPES = [
    "channels:history",
    "channels:read",
    "groups:history",
    "groups:read",
    "users:read",
    "users:read.email",
]


class SlackOAuth:
    """Slack OAuth handler."""
    
    @staticmethod
    def generate_oauth_url(state: str) -> str:
        """Generate the OAuth URL for Slack."""
        params = {
            "client_id": SLACK_CLIENT_ID,
            "redirect_uri": f"{WEB_DOMAIN}/oauth/callback",
            "scope": ",".join(SLACK_OAUTH_SCOPES),
            "state": state,
        }
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    
    @staticmethod
    def generate_dev_oauth_url(state: str) -> str:
        """Generate the OAuth URL for development."""
        return SlackOAuth.generate_oauth_url(state)
    
    @staticmethod
    def session_dump_json(email: str, redirect_on_success: str | None) -> str:
        """Create session data for OAuth flow."""
        return json.dumps({
            "email": email,
            "redirect_on_success": redirect_on_success,
            "provider": "slack",
        })
