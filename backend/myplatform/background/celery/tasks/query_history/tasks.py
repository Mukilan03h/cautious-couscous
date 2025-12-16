"""
Query History Export Celery tasks for MyPlatform.
Handles export of chat/query history to CSV files.
Ported from ee/esa/background/celery/tasks/query_history/tasks.py
"""
import csv
import io
from datetime import datetime

from celery import shared_task
from celery import Task

from esa.background.task_utils import construct_query_history_report_name
from esa.configs.app_configs import JOB_TIMEOUT
from esa.configs.app_configs import ONYX_QUERY_HISTORY_TYPE
from esa.configs.constants import FileOrigin
from esa.configs.constants import FileType
from esa.configs.constants import ESACeleryTask
from esa.configs.constants import QueryHistoryType
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.db.tasks import delete_task_with_id
from esa.db.tasks import mark_task_as_finished_with_id
from esa.db.tasks import mark_task_as_started_with_id
from esa.file_store.file_store import get_default_file_store
from esa.utils.logger import setup_logger


logger = setup_logger()

# Constant for anonymized email display
ONYX_ANONYMIZED_EMAIL = "anonymized@example.com"


@shared_task(
    name=ESACeleryTask.EXPORT_QUERY_HISTORY_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def export_query_history_task(
    self: Task,
    *,
    start: datetime,
    end: datetime,
    start_time: datetime,
    tenant_id: str,
) -> None:
    """
    Export query/chat history to a CSV file.
    
    Args:
        start: Start datetime for the export period
        end: End datetime for the export period
        start_time: When the task was initiated
        tenant_id: Tenant ID for multi-tenant setups
    """
    # Import here to avoid circular dependencies
    from myplatform.server.query_history.api import fetch_and_process_chat_session_history
    from myplatform.server.query_history.models import QuestionAnswerPairSnapshot
    
    if not self.request.id:
        raise RuntimeError("No task id defined for this task; cannot identify it")

    task_id = self.request.id
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=list(QuestionAnswerPairSnapshot.model_fields.keys()),
    )
    writer.writeheader()

    with get_session_with_current_tenant() as db_session:
        try:
            mark_task_as_started_with_id(
                db_session=db_session,
                task_id=task_id,
            )

            snapshot_generator = fetch_and_process_chat_session_history(
                db_session=db_session,
                start=start,
                end=end,
            )

            for snapshot in snapshot_generator:
                if ONYX_QUERY_HISTORY_TYPE == QueryHistoryType.ANONYMIZED:
                    snapshot.user_email = ONYX_ANONYMIZED_EMAIL

                writer.writerows(
                    qa_pair.to_json()
                    for qa_pair in QuestionAnswerPairSnapshot.from_chat_session_snapshot(
                        snapshot
                    )
                )

        except Exception:
            logger.exception(f"Failed to export query history with {task_id=}")
            mark_task_as_finished_with_id(
                db_session=db_session,
                task_id=task_id,
                success=False,
            )
            raise

    report_name = construct_query_history_report_name(task_id)
    with get_session_with_current_tenant() as db_session:
        try:
            stream.seek(0)
            get_default_file_store().save_file(
                content=stream,
                display_name=report_name,
                file_origin=FileOrigin.QUERY_HISTORY_CSV,
                file_type=FileType.CSV,
                file_metadata={
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "start_time": start_time.isoformat(),
                },
                file_id=report_name,
            )

            delete_task_with_id(
                db_session=db_session,
                task_id=task_id,
            )
            
            logger.info(
                f"Successfully exported query history for period "
                f"{start.isoformat()} to {end.isoformat()}"
            )
        except Exception:
            logger.exception(
                f"Failed to save query history export file; {report_name=}"
            )
            mark_task_as_finished_with_id(
                db_session=db_session,
                task_id=task_id,
                success=False,
            )
            raise
