"""
Team membership API endpoints.
Ported from ee/esa/server/tenants/team_membership_api.py
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from esa.auth.users import current_admin_user
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from myplatform.server.tenants.user_mapping import (
    get_users_for_tenant,
    remove_user_from_tenant,
    get_tenant_user_count,
)
from shared_configs.contextvars import get_current_tenant_id
from esa.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/tenants/members", tags=["Team Membership"])


class TeamMemberResponse(BaseModel):
    user_id: str
    email: str
    role: str
    status: str
    is_admin: bool


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("")
async def list_team_members(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[TeamMemberResponse]:
    """List all team members in the tenant."""
    tenant_id = get_current_tenant_id()
    
    users = get_users_for_tenant(db_session, tenant_id)
    
    return [
        TeamMemberResponse(
            user_id=str(u.id),
            email=u.email,
            role=getattr(u, "role", "user"),
            status="active",
            is_admin=getattr(u, "is_admin", False) or u.role.value == "admin" if hasattr(u, 'role') else False,
        )
        for u in users
    ]


@router.get("/count")
async def get_member_count(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Get the number of team members."""
    tenant_id = get_current_tenant_id()
    count = get_tenant_user_count(db_session, tenant_id)
    return {"count": count}


@router.put("/{user_id}/role")
async def update_member_role(
    user_id: str,
    request: UpdateRoleRequest,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Update a team member's role."""
    target_user = db_session.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update role logic
    if hasattr(target_user, 'role'):
        from esa.db.models import UserRole
        target_user.role = UserRole[request.role.upper()]
        db_session.commit()
    
    return {"message": "Role updated"}


@router.delete("/{user_id}")
async def remove_team_member(
    user_id: str,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Remove a user from the team."""
    if str(admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    success = remove_user_from_tenant(db_session, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User removed from team"}
