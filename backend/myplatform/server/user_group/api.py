"""
User group API endpoints.
Ported from ee/esa/server/user_group/api.py
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from esa.auth.users import current_admin_user
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from myplatform.db.user_groups import (
    create_user_group,
    get_all_user_groups,
    get_user_group_by_id,
    update_user_group,
    delete_user_group,
    add_user_to_group,
    remove_user_from_group,
)
from esa.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/user-groups", tags=["User Groups"])


class UserGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class UserGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class UserGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    user_count: int


class AddUserRequest(BaseModel):
    user_id: str


@router.get("", response_model=list[UserGroupResponse])
async def list_user_groups(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """List all user groups."""
    groups = get_all_user_groups(db_session)
    return [
        UserGroupResponse(
            id=g.id,
            name=g.name,
            description=getattr(g, 'description', None),
            user_count=len(getattr(g, 'users', [])),
        )
        for g in groups
    ]


@router.post("", response_model=UserGroupResponse)
async def create_group(
    request: UserGroupCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Create a new user group."""
    group = create_user_group(
        db_session=db_session,
        name=request.name,
        description=request.description,
    )
    
    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=getattr(group, 'description', None),
        user_count=0,
    )


@router.get("/{group_id}", response_model=UserGroupResponse)
async def get_group(
    group_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Get a user group by ID."""
    group = get_user_group_by_id(db_session, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=getattr(group, 'description', None),
        user_count=len(getattr(group, 'users', [])),
    )


@router.put("/{group_id}", response_model=UserGroupResponse)
async def update_group(
    group_id: int,
    request: UserGroupUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Update a user group."""
    group = update_user_group(
        db_session=db_session,
        group_id=group_id,
        name=request.name,
        description=request.description,
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=getattr(group, 'description', None),
        user_count=len(getattr(group, 'users', [])),
    )


@router.delete("/{group_id}")
async def delete_group_endpoint(
    group_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Delete a user group."""
    success = delete_user_group(db_session, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {"message": "Group deleted"}


@router.post("/{group_id}/users")
async def add_user_to_group_endpoint(
    group_id: int,
    request: AddUserRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Add a user to a group."""
    success = add_user_to_group(db_session, group_id, request.user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add user to group")
    
    return {"message": "User added to group"}


@router.delete("/{group_id}/users/{user_id}")
async def remove_user_from_group_endpoint(
    group_id: int,
    user_id: str,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """Remove a user from a group."""
    success = remove_user_from_group(db_session, group_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove user from group")
    
    return {"message": "User removed from group"}
