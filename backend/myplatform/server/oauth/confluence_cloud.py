"""
Confluence Cloud OAuth implementation for MyPlatform.
"""
import json
from urllib.parse import urlencode

from esa.configs.app_configs import WEB_DOMAIN
from esa.utils.logger import setup_logger

logger = setup_logger()

# Confluence OAuth configuration
CONFLUENCE_CLIENT_ID = ""  # Set via environment
CONFLUENCE_CLIENT_SECRET = ""  # Set via environment
CONFLUENCE_OAUTH_SCOPES = [
    "read:confluence-content.all",
    "read:confluence-space.summary",
    "read:confluence-user",
    "offline_access",
]


class ConfluenceCloudOAuth:
    """Confluence Cloud OAuth handler."""
    
    @staticmethod
    def generate_oauth_url(state: str) -> str:
        """Generate the OAuth URL for Confluence Cloud."""
        params = {
            "audience": "api.atlassian.com",
            "client_id": CONFLUENCE_CLIENT_ID,
            "redirect_uri": f"{WEB_DOMAIN}/oauth/callback",
            "response_type": "code",
            "scope": " ".join(CONFLUENCE_OAUTH_SCOPES),
            "state": state,
            "prompt": "consent",
        }
        return f"https://auth.atlassian.com/authorize?{urlencode(params)}"
    
    @staticmethod
    def generate_dev_oauth_url(state: str) -> str:
        """Generate the OAuth URL for development."""
        return ConfluenceCloudOAuth.generate_oauth_url(state)
    
    @staticmethod
    def session_dump_json(email: str, redirect_on_success: str | None) -> str:
        """Create session data for OAuth flow."""
        return json.dumps({
            "email": email,
            "redirect_on_success": redirect_on_success,
            "provider": "confluence_cloud",
        })
