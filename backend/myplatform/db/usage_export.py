"""
Usage export database operations for MyPlatform.
Ported from ee/esa/db/usage_export.py
"""
from datetime import datetime
from typing import BinaryIO

from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.file_store.file_store import get_default_file_store
from esa.utils.logger import setup_logger

logger = setup_logger()


class UsageReportMetadata(BaseModel):
    """Metadata for a usage report."""
    report_name: str
    created_at: datetime
    period_start: datetime | None = None
    period_end: datetime | None = None
    file_size: int = 0


def get_all_usage_reports(db_session: Session) -> list[UsageReportMetadata]:
    """
    Get metadata for all available usage reports.
    
    Args:
        db_session: Database session
        
    Returns:
        List of usage report metadata
    """
    file_store = get_default_file_store()
    reports = []
    
    # List files that match our usage report pattern
    try:
        files = file_store.list_files(prefix="usage_report_")
        for file_info in files:
            reports.append(UsageReportMetadata(
                report_name=file_info.get("name", ""),
                created_at=file_info.get("created_at", datetime.now()),
                file_size=file_info.get("size", 0),
            ))
    except Exception as e:
        logger.error(f"Failed to list usage reports: {e}")
    
    return reports


def get_usage_report_data(report_name: str) -> BinaryIO:
    """
    Get the data for a specific usage report.
    
    Args:
        report_name: Name of the report file
        
    Returns:
        Binary file-like object with report data
        
    Raises:
        ValueError: If report not found
    """
    file_store = get_default_file_store()
    
    try:
        file_data = file_store.get_file(report_name)
        if file_data is None:
            raise ValueError(f"Report not found: {report_name}")
        return file_data
    except Exception as e:
        logger.error(f"Failed to get usage report {report_name}: {e}")
        raise ValueError(f"Failed to retrieve report: {report_name}")
