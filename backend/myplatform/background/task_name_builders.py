"""
Task name builder utilities for MyPlatform background tasks.
Ported from ee/esa/background/task_name_builders.py
"""
from datetime import datetime

from esa.configs.constants import ESACeleryTask


QUERY_HISTORY_TASK_NAME_PREFIX = ESACeleryTask.EXPORT_QUERY_HISTORY_TASK


def name_chat_ttl_task(
    retention_limit_days: float, tenant_id: str | None = None
) -> str:
    """Generate a unique task name for chat TTL management tasks."""
    return f"chat_ttl_{retention_limit_days}_days"


def query_history_task_name(start: datetime, end: datetime) -> str:
    """Generate a unique task name for query history export tasks."""
    return f"{QUERY_HISTORY_TASK_NAME_PREFIX}_{start}_{end}"


def permission_sync_task_name(connector_id: int, credential_id: int) -> str:
    """Generate a unique task name for permission sync tasks."""
    return f"perm_sync_{connector_id}_{credential_id}"


def external_group_sync_task_name(tenant_id: str | None = None) -> str:
    """Generate a unique task name for external group sync tasks."""
    if tenant_id:
        return f"external_group_sync_{tenant_id}"
    return "external_group_sync"
