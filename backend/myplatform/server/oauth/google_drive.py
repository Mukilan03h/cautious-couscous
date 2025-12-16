"""
Google Drive OAuth implementation for MyPlatform.
"""
import json
from urllib.parse import urlencode

from esa.configs.app_configs import WEB_DOMAIN
from esa.utils.logger import setup_logger

logger = setup_logger()

# Google OAuth configuration
GOOGLE_OAUTH_CLIENT_ID = ""  # Set via environment
GOOGLE_OAUTH_CLIENT_SECRET = ""  # Set via environment
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleDriveOAuth:
    """Google Drive OAuth handler."""
    
    @staticmethod
    def generate_oauth_url(state: str) -> str:
        """Generate the OAuth URL for Google Drive."""
        params = {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": f"{WEB_DOMAIN}/oauth/callback",
            "response_type": "code",
            "scope": " ".join(GOOGLE_OAUTH_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    @staticmethod
    def generate_dev_oauth_url(state: str) -> str:
        """Generate the OAuth URL for development."""
        return GoogleDriveOAuth.generate_oauth_url(state)
    
    @staticmethod
    def session_dump_json(email: str, redirect_on_success: str | None) -> str:
        """Create session data for OAuth flow."""
        return json.dumps({
            "email": email,
            "redirect_on_success": redirect_on_success,
            "provider": "google_drive",
        })
