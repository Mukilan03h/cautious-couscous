"""
Usage export API endpoints for MyPlatform.
Ported from ee/esa/server/reporting/usage_export_api.py
"""
from collections.abc import Generator
from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from myplatform.db.usage_export import get_all_usage_reports
from myplatform.db.usage_export import get_usage_report_data
from myplatform.db.usage_export import UsageReportMetadata
from esa.auth.users import current_admin_user
from esa.background.celery.versioned_apps.client import app as client_app
from esa.configs.constants import ESACeleryTask
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from esa.file_store.constants import STANDARD_CHUNK_SIZE
from shared_configs.contextvars import get_current_tenant_id

router = APIRouter()


class GenerateUsageReportParams(BaseModel):
    """Parameters for generating a usage report."""
    period_from: str | None = None
    period_to: str | None = None


@router.post("/admin/usage-report", status_code=204)
def generate_report(
    params: GenerateUsageReportParams,
    user: User = Depends(current_admin_user),
) -> None:
    """
    Generate a new usage report (async task).
    
    Args:
        params: Report generation parameters
        user: The current admin user
    """
    # Validate period parameters
    if params.period_from and params.period_to:
        try:
            datetime.fromisoformat(params.period_from)
            datetime.fromisoformat(params.period_to)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    tenant_id = get_current_tenant_id()
    client_app.send_task(
        ESACeleryTask.GENERATE_USAGE_REPORT_TASK,
        kwargs={
            "tenant_id": tenant_id,
            "user_id": str(user.id) if user else None,
            "period_from": params.period_from,
            "period_to": params.period_to,
        },
    )

    return None


@router.get("/admin/usage-report/{report_name}")
def read_usage_report(
    report_name: str,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> Response:
    """
    Download a specific usage report.
    
    Args:
        report_name: Name of the report to download
    """
    try:
        file = get_usage_report_data(report_name)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    def iterfile() -> Generator[bytes, None, None]:
        while True:
            chunk = file.read(STANDARD_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        content=iterfile(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={report_name}"},
    )


@router.get("/admin/usage-report")
def fetch_usage_reports(
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[UsageReportMetadata]:
    """Fetch all available usage reports."""
    try:
        return get_all_usage_reports(db_session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
