"""
Custom Connector Permission Sync API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.connector_permissions import (
    enable_connector_sync,
    get_connector_sync_status,
    update_sync_status,
    CustomConnectorPermissionSync,
)


router = APIRouter(prefix="/api/admin/connector-sync", tags=["connector-sync"])


class SyncEnableRequest(BaseModel):
    connector_id: int
    connector_type: str  # slack, google_drive, sharepoint, confluence, github, jira
    config: Optional[dict] = None


class SyncStatusResponse(BaseModel):
    connector_id: int
    connector_type: str
    sync_enabled: bool
    sync_status: str
    last_sync_at: Optional[datetime]
    last_error: Optional[str]


@router.post("/enable", response_model=SyncStatusResponse)
def enable_sync(
    request: SyncEnableRequest,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Enable permission sync for a connector"""
    sync = enable_connector_sync(
        db,
        connector_id=request.connector_id,
        connector_type=request.connector_type,
        sync_config=request.config,
    )
    return SyncStatusResponse(
        connector_id=sync.connector_id,
        connector_type=sync.connector_type,
        sync_enabled=sync.sync_enabled,
        sync_status=sync.sync_status,
        last_sync_at=sync.last_sync_at,
        last_error=sync.last_error,
    )


@router.get("/{connector_id}", response_model=Optional[SyncStatusResponse])
def get_sync_status(
    connector_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Get sync status for a connector"""
    sync = get_connector_sync_status(db, connector_id)
    if not sync:
        return None
    return SyncStatusResponse(
        connector_id=sync.connector_id,
        connector_type=sync.connector_type,
        sync_enabled=sync.sync_enabled,
        sync_status=sync.sync_status,
        last_sync_at=sync.last_sync_at,
        last_error=sync.last_error,
    )


@router.post("/{connector_id}/trigger")
def trigger_sync(
    connector_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Trigger a permission sync (async job would handle actual sync)"""
    update_sync_status(db, connector_id, 'pending')
    # In production, this would queue a background job
    return {"status": "sync_queued", "connector_id": connector_id}
