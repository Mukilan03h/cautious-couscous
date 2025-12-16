"""
Cleanup Celery tasks for MyPlatform.
Handles cleanup of old export tasks and other maintenance operations.
Ported from ee/esa/background/celery/tasks/cleanup/tasks.py
"""
from datetime import datetime
from datetime import timedelta

from celery import shared_task

from myplatform.db.query_history import get_all_query_history_export_tasks
from esa.configs.app_configs import JOB_TIMEOUT
from esa.configs.constants import ESACeleryTask
from esa.db.engine.sql_engine import get_session_with_tenant
from esa.db.enums import TaskStatus
from esa.db.tasks import delete_task_with_id
from esa.utils.logger import setup_logger


logger = setup_logger()


@shared_task(
    name=ESACeleryTask.EXPORT_QUERY_HISTORY_CLEANUP_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
)
def export_query_history_cleanup_task(*, tenant_id: str) -> None:
    """
    Clean up old query history export tasks.
    
    - Successful tasks are deleted immediately
    - Failed tasks are kept for 24 hours for debugging, then deleted
    
    Args:
        tenant_id: Tenant ID for multi-tenant setups
    """
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        tasks = get_all_query_history_export_tasks(db_session=db_session)

        deleted_count = 0
        for task in tasks:
            if task.status == TaskStatus.SUCCESS:
                delete_task_with_id(db_session=db_session, task_id=task.task_id)
                deleted_count += 1
            elif task.status == TaskStatus.FAILURE:
                if task.start_time:
                    # Keep failed tasks for 24 hours for debugging
                    deadline = task.start_time + timedelta(hours=24)
                    now = datetime.now()
                    if now < deadline:
                        continue

                logger.error(
                    f"Task with {task.task_id=} failed; it is being deleted now"
                )
                delete_task_with_id(db_session=db_session, task_id=task.task_id)
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old export tasks")
