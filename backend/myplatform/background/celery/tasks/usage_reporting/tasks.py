"""
Usage Reporting Celery tasks for MyPlatform.
Handles generation of usage reports for analytics.
Ported from ee/esa/background/celery/tasks/usage_reporting/tasks.py
"""
from datetime import datetime
from uuid import UUID

from celery import shared_task
from celery import Task

from esa.configs.app_configs import JOB_TIMEOUT
from esa.configs.constants import ESACeleryTask
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=ESACeleryTask.GENERATE_USAGE_REPORT_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def generate_usage_report_task(
    self: Task,
    *,
    tenant_id: str,
    user_id: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
) -> None:
    """
    User-initiated usage report generation task.
    
    Args:
        tenant_id: Tenant ID for multi-tenant setups
        user_id: Optional user ID who requested the report
        period_from: ISO format start date for the report period
        period_to: ISO format end date for the report period
    """
    # Import here to avoid circular dependencies
    from myplatform.server.reporting.usage_export_generation import create_new_usage_report
    
    # Parse period if provided
    period = None
    if period_from and period_to:
        period = (
            datetime.fromisoformat(period_from),
            datetime.fromisoformat(period_to),
        )

    logger.info(
        f"Generating usage report for tenant {tenant_id}, "
        f"period: {period_from} to {period_to}"
    )

    # Generate the report
    with get_session_with_current_tenant() as db_session:
        create_new_usage_report(
            db_session=db_session,
            user_id=UUID(user_id) if user_id else None,
            period=period,
        )

    logger.info("Usage report generation completed")
