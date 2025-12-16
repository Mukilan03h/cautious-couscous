"""
Application configurations for MyPlatform.
Ported from ee/esa/configs/app_configs.py
"""
import json
import os


#####
# Auto Permission Sync
#####
# should generally only be used for sources that support polling of permissions
# e.g. can pull in only permission changes rather than having to go through all
# documents every time
DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY") or 5 * 60
)


#####
# Confluence
#####
CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY = int(
    os.environ.get("CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY") or 30 * 60
)
CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY") or 30 * 60
)
CONFLUENCE_ANONYMOUS_ACCESS_IS_PUBLIC = (
    os.environ.get("CONFLUENCE_ANONYMOUS_ACCESS_IS_PUBLIC", "").lower() == "true"
)


#####
# JIRA
#####
JIRA_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("JIRA_PERMISSION_DOC_SYNC_FREQUENCY") or 30 * 60
)
JIRA_PERMISSION_GROUP_SYNC_FREQUENCY = int(
    os.environ.get("JIRA_PERMISSION_GROUP_SYNC_FREQUENCY") or 30 * 60
)


#####
# Google Drive
#####
GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY = int(
    os.environ.get("GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY") or 5 * 60
)


#####
# GitHub
#####
GITHUB_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("GITHUB_PERMISSION_DOC_SYNC_FREQUENCY") or 5 * 60
)
GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY = int(
    os.environ.get("GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY") or 5 * 60
)


#####
# Slack
#####
SLACK_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("SLACK_PERMISSION_DOC_SYNC_FREQUENCY") or 5 * 60
)

NUM_PERMISSION_WORKERS = int(os.environ.get("NUM_PERMISSION_WORKERS") or 2)


#####
# Teams
#####
TEAMS_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("TEAMS_PERMISSION_DOC_SYNC_FREQUENCY") or 5 * 60
)


#####
# SharePoint
#####
SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY = int(
    os.environ.get("SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY") or 30 * 60
)
SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY = int(
    os.environ.get("SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY") or 5 * 60
)


####
# Celery Job Frequency
####
CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS = float(
    os.environ.get("CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS") or 1
)


#####
# Billing / Stripe
#####
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE")


#####
# LLM API Keys
#####
OPENAI_DEFAULT_API_KEY = os.environ.get("OPENAI_DEFAULT_API_KEY")
ANTHROPIC_DEFAULT_API_KEY = os.environ.get("ANTHROPIC_DEFAULT_API_KEY")
COHERE_DEFAULT_API_KEY = os.environ.get("COHERE_DEFAULT_API_KEY")


#####
# JWT Configuration
#####
JWT_PUBLIC_KEY_URL: str | None = os.getenv("JWT_PUBLIC_KEY_URL", None)


#####
# Super Users
#####
SUPER_USERS = json.loads(os.environ.get("SUPER_USERS", "[]"))
SUPER_CLOUD_API_KEY = os.environ.get("SUPER_CLOUD_API_KEY", "api_key")


#####
# Analytics / PostHog
#####
POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY") or "FooBar"
POSTHOG_HOST = os.environ.get("POSTHOG_HOST") or "https://us.i.posthog.com"
MARKETING_POSTHOG_API_KEY = os.environ.get("MARKETING_POSTHOG_API_KEY")


#####
# Marketing / Tracking
#####
HUBSPOT_TRACKING_URL = os.environ.get("HUBSPOT_TRACKING_URL")


#####
# Tenant Gating
#####
GATED_TENANTS_KEY = "gated_tenants"
