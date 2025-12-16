"""
Slack external permissions utilities.
Ported from ee/esa/external_permissions/slack/utils.py
"""
from slack_sdk import WebClient

from esa.connectors.slack.utils import make_paginated_slack_api_call


def fetch_user_id_to_email_map(
    slack_client: WebClient,
) -> dict[str, str]:
    user_id_to_email_map = {}
    for user_info in make_paginated_slack_api_call(
        slack_client.users_list,
    ):
        for user in user_info.get("members", []):
            if user.get("profile", {}).get("email"):
                user_id_to_email_map[user.get("id")] = user.get("profile", {}).get(
                    "email"
                )
    return user_id_to_email_map
