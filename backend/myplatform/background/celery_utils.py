"""
Celery utility functions for MyPlatform background tasks.
Ported from ee/esa/background/celery_utils.py
"""
from sqlalchemy.orm import Session

from myplatform.background.task_name_builders import name_chat_ttl_task
from esa.db.tasks import check_task_is_live_and_not_timed_out
from esa.db.tasks import get_latest_task
from esa.utils.logger import setup_logger

logger = setup_logger()


def should_perform_chat_ttl_check(
    retention_limit_days: float | None, db_session: Session
) -> bool:
    """
    Check if a chat TTL cleanup task should be performed.
    
    Args:
        retention_limit_days: Number of days to retain chat sessions
        db_session: Database session
        
    Returns:
        True if TTL check should be performed, False otherwise
    """
    # TODO: make this a check for None and add behavior for 0 day TTL
    if not retention_limit_days:
        return False

    task_name = name_chat_ttl_task(retention_limit_days)
    latest_task = get_latest_task(task_name, db_session)
    if not latest_task:
        return True

    if check_task_is_live_and_not_timed_out(latest_task, db_session):
        logger.debug(f"{task_name} is already being performed. Skipping.")
        return False
    return True


def should_perform_permission_sync(
    connector_id: int, credential_id: int, db_session: Session
) -> bool:
    """
    Check if a permission sync task should be performed.
    
    Args:
        connector_id: The connector ID
        credential_id: The credential ID
        db_session: Database session
        
    Returns:
        True if permission sync should be performed, False otherwise
    """
    from myplatform.background.task_name_builders import permission_sync_task_name
    
    task_name = permission_sync_task_name(connector_id, credential_id)
    latest_task = get_latest_task(task_name, db_session)
    if not latest_task:
        return True

    if check_task_is_live_and_not_timed_out(latest_task, db_session):
        logger.debug(f"{task_name} is already being performed. Skipping.")
        return False
    return True


def should_perform_external_group_sync(
    tenant_id: str | None, db_session: Session
) -> bool:
    """
    Check if an external group sync task should be performed.
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant setups
        db_session: Database session
        
    Returns:
        True if external group sync should be performed, False otherwise
    """
    from myplatform.background.task_name_builders import external_group_sync_task_name
    
    task_name = external_group_sync_task_name(tenant_id)
    latest_task = get_latest_task(task_name, db_session)
    if not latest_task:
        return True

    if check_task_is_live_and_not_timed_out(latest_task, db_session):
        logger.debug(f"{task_name} is already being performed. Skipping.")
        return False
    return True
