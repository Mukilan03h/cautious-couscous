"""
Custom Multi-Tenancy API
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user, current_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.tenants import (
    create_tenant,
    get_tenant_by_id,
    get_tenant_by_slug,
    get_all_tenants,
    update_tenant,
    add_user_to_tenant,
    remove_user_from_tenant,
    get_user_tenants,
    get_tenant_users,
    CustomTenant,
)


router = APIRouter(prefix="/api/admin/tenants", tags=["tenants"])
user_router = APIRouter(prefix="/api/tenants", tags=["my-tenants"])


class TenantCreate(BaseModel):
    name: str
    slug: str
    display_name: Optional[str] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    settings: Optional[dict] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    max_users: Optional[int] = None
    settings: Optional[dict] = None


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    display_name: Optional[str]
    is_active: bool
    max_users: Optional[int]
    max_documents: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantUserAdd(BaseModel):
    user_id: str  # UUID
    role: str = "member"


class TenantUserResponse(BaseModel):
    user_id: str
    role: str
    is_active: bool


# ============ Admin Endpoints ============

@router.get("/", response_model=List[TenantResponse])
def list_tenants(
    include_inactive: bool = False,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List all tenants"""
    tenants = get_all_tenants(db, active_only=not include_inactive)
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            display_name=t.display_name,
            is_active=t.is_active,
            max_users=t.max_users,
            max_documents=t.max_documents,
            created_at=t.created_at,
        )
        for t in tenants
    ]


@router.post("/", response_model=TenantResponse)
def create_new_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new tenant"""
    t = create_tenant(
        db,
        name=tenant.name,
        slug=tenant.slug,
        display_name=tenant.display_name,
        max_users=tenant.max_users,
        max_documents=tenant.max_documents,
        settings=tenant.settings,
    )
    return TenantResponse(
        id=t.id,
        name=t.name,
        slug=t.slug,
        display_name=t.display_name,
        is_active=t.is_active,
        max_users=t.max_users,
        max_documents=t.max_documents,
        created_at=t.created_at,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Get tenant by ID"""
    t = get_tenant_by_id(db, tenant_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=t.id,
        name=t.name,
        slug=t.slug,
        display_name=t.display_name,
        is_active=t.is_active,
        max_users=t.max_users,
        max_documents=t.max_documents,
        created_at=t.created_at,
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_existing_tenant(
    tenant_id: int,
    update: TenantUpdate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Update a tenant"""
    t = update_tenant(
        db,
        tenant_id=tenant_id,
        name=update.name,
        display_name=update.display_name,
        is_active=update.is_active,
        max_users=update.max_users,
        settings=update.settings,
    )
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=t.id,
        name=t.name,
        slug=t.slug,
        display_name=t.display_name,
        is_active=t.is_active,
        max_users=t.max_users,
        max_documents=t.max_documents,
        created_at=t.created_at,
    )


@router.post("/{tenant_id}/users")
def add_user(
    tenant_id: int,
    user_data: TenantUserAdd,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Add user to tenant"""
    membership = add_user_to_tenant(db, tenant_id, UUID(user_data.user_id), user_data.role)
    return {"added": True, "user_id": user_data.user_id, "role": membership.role}


@router.delete("/{tenant_id}/users/{user_id}")
def remove_user(
    tenant_id: int,
    user_id: str,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Remove user from tenant"""
    removed = remove_user_from_tenant(db, tenant_id, UUID(user_id))
    return {"removed": removed, "user_id": user_id}


@router.get("/{tenant_id}/users", response_model=List[TenantUserResponse])
def list_tenant_users(
    tenant_id: int,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """List users in a tenant"""
    users = get_tenant_users(db, tenant_id)
    return [
        TenantUserResponse(
            user_id=str(u.user_id),
            role=u.role,
            is_active=u.is_active,
        )
        for u in users
    ]


# ============ User Endpoints ============

@user_router.get("/my-tenants")
def get_my_tenants(
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Get tenants current user belongs to"""
    tenant_ids = get_user_tenants(db, user.id)
    tenants = [get_tenant_by_id(db, tid) for tid in tenant_ids]
    return {
        "tenants": [
            {"id": t.id, "name": t.name, "slug": t.slug, "display_name": t.display_name}
            for t in tenants if t
        ]
    }
