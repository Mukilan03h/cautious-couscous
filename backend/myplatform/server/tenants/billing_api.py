"""
Billing API endpoints for tenants.
Ported from ee/esa/server/tenants/billing_api.py
"""
from fastapi import APIRouter, Depends, HTTPException

from myplatform.server.tenants.billing import (
    fetch_billing_information,
    fetch_stripe_checkout_session,
    register_tenant_users,
)
from myplatform.server.tenants.models import BillingInformation, SubscriptionStatusResponse
from esa.auth.users import current_admin_user
from esa.db.models import User
from shared_configs.contextvars import get_current_tenant_id
from esa.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/tenants/billing", tags=["Tenant Billing"])


@router.get("")
async def get_billing_info(
    user: User = Depends(current_admin_user),
) -> BillingInformation | SubscriptionStatusResponse:
    """Get billing information for the current tenant."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")
    
    try:
        return fetch_billing_information(tenant_id)
    except Exception as e:
        logger.error(f"Error fetching billing info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/checkout-session")
async def create_checkout_session(
    user: User = Depends(current_admin_user),
) -> dict:
    """Create a Stripe checkout session."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")
    
    try:
        session_id = fetch_stripe_checkout_session(tenant_id)
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-seats")
async def update_seat_count(
    seats: int,
    user: User = Depends(current_admin_user),
) -> dict:
    """Update the number of seats in the subscription."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")
    
    if seats < 1:
        raise HTTPException(status_code=400, detail="Seats must be at least 1")
    
    try:
        subscription = register_tenant_users(tenant_id, seats)
        return {"success": True, "subscription_id": subscription.id}
    except Exception as e:
        logger.error(f"Error updating seats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
