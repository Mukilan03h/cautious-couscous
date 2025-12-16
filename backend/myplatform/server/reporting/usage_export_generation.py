"""
Usage report generation for MyPlatform.
Ported from ee/esa/server/reporting/usage_export_generation.py
"""
import csv
import io
import zipfile
from datetime import datetime
from datetime import timezone
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.orm import Session

from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.file_store.file_store import get_default_file_store
from esa.utils.logger import setup_logger

logger = setup_logger()


def create_new_usage_report(
    db_session: Session,
    user_id: UUID | None = None,
    period: tuple[datetime, datetime] | None = None,
) -> str:
    """
    Create a new usage report.
    
    Args:
        db_session: Database session
        user_id: Optional user ID who requested the report
        period: Optional tuple of (start_date, end_date)
        
    Returns:
        The report filename
    """
    now = datetime.now(tz=timezone.utc)
    report_name = f"usage_report_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    
    # Create report data
    report_data = _generate_usage_data(db_session, period)
    
    # Create ZIP file with CSV
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add summary CSV
        summary_csv = io.StringIO()
        writer = csv.writer(summary_csv)
        writer.writerow(['Metric', 'Value'])
        for key, value in report_data.items():
            writer.writerow([key, value])
        zip_file.writestr('summary.csv', summary_csv.getvalue())
    
    zip_buffer.seek(0)
    
    # Save to file store
    file_store = get_default_file_store()
    file_store.save_file_from_bytes(
        file_id=report_name,
        content=zip_buffer.read(),
        content_type="application/zip",
    )
    
    logger.info(f"Usage report created: {report_name}")
    return report_name


def _generate_usage_data(
    db_session: Session,
    period: tuple[datetime, datetime] | None = None,
) -> dict:
    """Generate usage data for the report."""
    # Placeholder - actual implementation would query:
    # - Chat sessions count
    # - Messages count
    # - Unique users
    # - Token usage
    # - Connector indexing stats
    
    data = {
        "report_generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_chat_sessions": 0,
        "total_messages": 0,
        "unique_users": 0,
        "total_tokens_used": 0,
        "documents_indexed": 0,
    }
    
    if period:
        data["period_start"] = period[0].isoformat()
        data["period_end"] = period[1].isoformat()
    
    return data
