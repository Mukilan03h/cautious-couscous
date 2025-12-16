"""
Tenant models for MyPlatform.
Ported from ee/esa/server/tenants/models.py
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BillingInformation(BaseModel):
    """Billing information for a tenant."""
    stripe_subscription_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    number_of_seats: int
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    seats: int = 1
    payment_method_enabled: bool = False


class SubscriptionStatusResponse(BaseModel):
    """Response for subscription status check."""
    subscribed: bool
    message: Optional[str] = None


class TenantCreationRequest(BaseModel):
    """Request to create a new tenant."""
    email: str
    referral_source: Optional[str] = None


class TenantInfo(BaseModel):
    """Information about a tenant."""
    tenant_id: str
    email: str
    created_at: datetime
    is_active: bool = True
    plan: Optional[str] = None


class TenantProvisioningResponse(BaseModel):
    """Response after tenant provisioning."""
    tenant_id: str
    success: bool
    message: Optional[str] = None


class UserInvitation(BaseModel):
    """User invitation model."""
    email: str
    role: str = "user"
    invited_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class TeamMember(BaseModel):
    """Team member model."""
    user_id: str
    email: str
    role: str
    status: str
    joined_at: Optional[datetime] = None


class ProductGatingConfig(BaseModel):
    """Configuration for product gating."""
    feature_name: str
    is_enabled: bool
    requires_subscription: bool = False
    min_plan: Optional[str] = None


class CheckoutSessionCreationRequest(BaseModel):
    quantity: int


class CreateTenantRequest(BaseModel):
    tenant_id: str
    initial_admin_email: str


class ProductGatingRequest(BaseModel):
    tenant_id: str
    application_status: str


class ProductGatingFullSyncRequest(BaseModel):
    gated_tenant_ids: list[str]


class CheckoutSessionCreationResponse(BaseModel):
    id: str


class ImpersonateRequest(BaseModel):
    email: str


class TenantCreationPayload(BaseModel):
    tenant_id: str
    email: str
    referral_source: Optional[str] = None


class TenantDeletionPayload(BaseModel):
    tenant_id: str
    email: str


class AnonymousUserPath(BaseModel):
    anonymous_user_path: Optional[str] = None


class ProductGatingResponse(BaseModel):
    updated: bool
    error: Optional[str] = None


class SubscriptionSessionResponse(BaseModel):
    sessionId: str


class TenantByDomainResponse(BaseModel):
    tenant_id: str
    number_of_users: int
    creator_email: str


class TenantByDomainRequest(BaseModel):
    email: str


class RequestInviteRequest(BaseModel):
    tenant_id: str


class RequestInviteResponse(BaseModel):
    success: bool
    message: str


class PendingUserSnapshot(BaseModel):
    email: str


class ApproveUserRequest(BaseModel):
    email: str
