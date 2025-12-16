"""
Custom Multi-Tenancy - Tenant isolation and management
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Session

from esa.db.models import Base


class CustomTenant(Base):
    """Tenant (organization) for multi-tenancy"""
    __tablename__ = "custom_tenant"
    
    id = Column(Integer, primary_key=True)
    
    # Tenant info
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Limits
    max_users = Column(Integer, nullable=True)
    max_documents = Column(Integer, nullable=True)
    max_storage_gb = Column(Integer, nullable=True)
    
    # Settings
    settings = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomTenantUser(Base):
    """User membership in tenants"""
    __tablename__ = "custom_tenant_user"
    
    id = Column(Integer, primary_key=True)
    
    tenant_id = Column(Integer, ForeignKey("custom_tenant.id"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Role within tenant
    role = Column(String, default='member')  # admin, member, viewer
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============ Tenant Functions ============

def create_tenant(
    db_session: Session,
    name: str,
    slug: str,
    display_name: str = None,
    max_users: int = None,
    max_documents: int = None,
    settings: dict = None,
) -> CustomTenant:
    """Create a new tenant"""
    tenant = CustomTenant(
        name=name,
        slug=slug,
        display_name=display_name,
        max_users=max_users,
        max_documents=max_documents,
        settings=settings or {},
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def get_tenant_by_slug(db_session: Session, slug: str) -> CustomTenant | None:
    """Get tenant by slug"""
    return db_session.scalar(
        select(CustomTenant).where(CustomTenant.slug == slug)
    )


def get_tenant_by_id(db_session: Session, tenant_id: int) -> CustomTenant | None:
    """Get tenant by ID"""
    return db_session.get(CustomTenant, tenant_id)


def get_all_tenants(db_session: Session, active_only: bool = True) -> List[CustomTenant]:
    """Get all tenants"""
    stmt = select(CustomTenant)
    if active_only:
        stmt = stmt.where(CustomTenant.is_active == True)
    return list(db_session.scalars(stmt).all())


def update_tenant(
    db_session: Session,
    tenant_id: int,
    name: str = None,
    display_name: str = None,
    is_active: bool = None,
    max_users: int = None,
    settings: dict = None,
) -> CustomTenant | None:
    """Update tenant"""
    tenant = get_tenant_by_id(db_session, tenant_id)
    if not tenant:
        return None
    
    if name is not None:
        tenant.name = name
    if display_name is not None:
        tenant.display_name = display_name
    if is_active is not None:
        tenant.is_active = is_active
    if max_users is not None:
        tenant.max_users = max_users
    if settings is not None:
        tenant.settings = settings
    
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


# ============ Tenant User Functions ============

def add_user_to_tenant(
    db_session: Session,
    tenant_id: int,
    user_id: UUID,
    role: str = 'member',
) -> CustomTenantUser:
    """Add user to tenant"""
    # Check if exists
    stmt = select(CustomTenantUser).where(
        CustomTenantUser.tenant_id == tenant_id,
        CustomTenantUser.user_id == user_id,
    )
    membership = db_session.scalar(stmt)
    
    if membership:
        membership.role = role
        membership.is_active = True
    else:
        membership = CustomTenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        db_session.add(membership)
    
    db_session.commit()
    db_session.refresh(membership)
    return membership


def remove_user_from_tenant(
    db_session: Session,
    tenant_id: int,
    user_id: UUID,
) -> bool:
    """Remove user from tenant"""
    stmt = select(CustomTenantUser).where(
        CustomTenantUser.tenant_id == tenant_id,
        CustomTenantUser.user_id == user_id,
    )
    membership = db_session.scalar(stmt)
    
    if membership:
        membership.is_active = False
        db_session.commit()
        return True
    return False


def get_user_tenants(db_session: Session, user_id: UUID) -> List[int]:
    """Get all tenant IDs for a user"""
    stmt = select(CustomTenantUser.tenant_id).where(
        CustomTenantUser.user_id == user_id,
        CustomTenantUser.is_active == True,
    )
    return list(db_session.scalars(stmt).all())


def get_tenant_users(db_session: Session, tenant_id: int) -> List[CustomTenantUser]:
    """Get all users in a tenant"""
    stmt = select(CustomTenantUser).where(
        CustomTenantUser.tenant_id == tenant_id,
        CustomTenantUser.is_active == True,
    )
    return list(db_session.scalars(stmt).all())


def check_user_in_tenant(
    db_session: Session,
    user_id: UUID,
    tenant_id: int,
) -> bool:
    """Check if user is in tenant"""
    stmt = select(CustomTenantUser).where(
        CustomTenantUser.user_id == user_id,
        CustomTenantUser.tenant_id == tenant_id,
        CustomTenantUser.is_active == True,
    )
    return db_session.scalar(stmt) is not None


def get_user_tenant_role(
    db_session: Session,
    user_id: UUID,
    tenant_id: int,
) -> str | None:
    """Get user's role in a tenant"""
    stmt = select(CustomTenantUser).where(
        CustomTenantUser.user_id == user_id,
        CustomTenantUser.tenant_id == tenant_id,
        CustomTenantUser.is_active == True,
    )
    membership = db_session.scalar(stmt)
    return membership.role if membership else None
