"""
User invitation API endpoints.
Ported from ee/esa/server/tenants/user_invitations_api.py
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from shared_configs.contextvars import get_current_tenant_id
from esa.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/tenants/invitations", tags=["User Invitations"])


class InvitationRequest(BaseModel):
    email: str
    role: str = "user"


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    invite_link: Optional[str]
    expires_at: datetime


# In-memory storage for invitations (in production, use database)
_invitations: dict[str, dict] = {}


@router.post("")
async def create_invitation(
    request: InvitationRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> InvitationResponse:
    """Create a user invitation."""
    tenant_id = get_current_tenant_id()
    
    invite_id = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = {
        "id": invite_id,
        "tenant_id": tenant_id,
        "email": request.email,
        "role": request.role,
        "status": "pending",
        "expires_at": expires_at,
        "invited_by": user.email,
    }
    
    _invitations[invite_id] = invitation
    
    # Generate invite link
    invite_link = f"/invite/{invite_id}"
    
    return InvitationResponse(
        id=invite_id,
        email=request.email,
        role=request.role,
        status="pending",
        invite_link=invite_link,
        expires_at=expires_at,
    )


@router.get("")
async def list_invitations(
    user: User = Depends(current_admin_user),
) -> list[InvitationResponse]:
    """List all pending invitations for the tenant."""
    tenant_id = get_current_tenant_id()
    
    tenant_invitations = [
        InvitationResponse(
            id=inv["id"],
            email=inv["email"],
            role=inv["role"],
            status=inv["status"],
            invite_link=f"/invite/{inv['id']}",
            expires_at=inv["expires_at"],
        )
        for inv in _invitations.values()
        if inv.get("tenant_id") == tenant_id and inv["status"] == "pending"
    ]
    
    return tenant_invitations


@router.delete("/{invite_id}")
async def revoke_invitation(
    invite_id: str,
    user: User = Depends(current_admin_user),
) -> dict:
    """Revoke a pending invitation."""
    if invite_id not in _invitations:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    tenant_id = get_current_tenant_id()
    if _invitations[invite_id].get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    _invitations[invite_id]["status"] = "revoked"
    return {"message": "Invitation revoked"}
