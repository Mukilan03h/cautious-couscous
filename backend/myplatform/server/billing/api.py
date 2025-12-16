"""
Billing API endpoints for MyPlatform.
Handles subscription management and billing portal access.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import os

from esa.auth.users import current_admin_user
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from esa.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/billing", tags=["Billing"])

# Stripe configuration from environment
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")


class BillingInfo(BaseModel):
    stripe_subscription_id: str
    status: str
    current_period_start: str
    current_period_end: str
    number_of_seats: int
    cancel_at_period_end: bool
    canceled_at: Optional[str]
    trial_start: Optional[str]
    trial_end: Optional[str]
    seats: int
    payment_method_enabled: bool


class CustomerPortalResponse(BaseModel):
    url: str


@router.get("", response_model=BillingInfo)
async def get_billing_info(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
):
    """
    Get billing information for the current tenant.
    """
    tenant_id = get_current_tenant_id()
    
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Please set STRIPE_SECRET_KEY."
        )
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get tenant's subscription from database or Stripe
        # This would typically query a tenant_billing table
        # For now, we'll try to get from Stripe customer metadata
        
        # Get customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            raise HTTPException(
                status_code=404,
                detail="No billing account found for this user."
            )
        
        customer = customers.data[0]
        
        # Get active subscriptions
        subscriptions = stripe.Subscription.list(
            customer=customer.id,
            status="all",
            limit=1,
        )
        
        if not subscriptions.data:
            raise HTTPException(
                status_code=404,
                detail="No subscription found for this account."
            )
        
        sub = subscriptions.data[0]
        
        # Get payment methods
        payment_methods = stripe.PaymentMethod.list(
            customer=customer.id,
            type="card",
        )
        
        return BillingInfo(
            stripe_subscription_id=sub.id,
            status=sub.status,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            number_of_seats=sub.quantity or 1,
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=str(sub.canceled_at) if sub.canceled_at else None,
            trial_start=str(sub.trial_start) if sub.trial_start else None,
            trial_end=str(sub.trial_end) if sub.trial_end else None,
            seats=sub.quantity or 1,
            payment_method_enabled=len(payment_methods.data) > 0,
        )
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Stripe library not installed. Run: pip install stripe"
        )
    except Exception as e:
        logger.error(f"Error fetching billing info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching billing information: {str(e)}"
        )


@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal_session(
    user: User = Depends(current_admin_user),
):
    """
    Create a Stripe Customer Portal session for subscription management.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Please set STRIPE_SECRET_KEY."
        )
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            raise HTTPException(
                status_code=404,
                detail="No billing account found for this user."
            )
        
        customer = customers.data[0]
        
        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=os.environ.get("WEB_DOMAIN", "http://localhost:3000") + "/myplatform/admin/billing",
        )
        
        return CustomerPortalResponse(url=session.url)
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Stripe library not installed. Run: pip install stripe"
        )
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating billing portal session: {str(e)}"
        )


@router.post("/update-seats")
async def update_seat_count(
    seats: int,
    user: User = Depends(current_admin_user),
):
    """
    Update the number of seats in the subscription.
    """
    if seats < 1:
        raise HTTPException(status_code=400, detail="Seat count must be at least 1")
    
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured."
        )
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get customer
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            raise HTTPException(status_code=404, detail="No billing account found.")
        
        customer = customers.data[0]
        
        # Get subscription
        subscriptions = stripe.Subscription.list(
            customer=customer.id,
            status="active",
            limit=1,
        )
        
        if not subscriptions.data:
            raise HTTPException(status_code=404, detail="No active subscription found.")
        
        sub = subscriptions.data[0]
        
        # Update subscription quantity
        stripe.Subscription.modify(
            sub.id,
            items=[{
                "id": sub["items"]["data"][0].id,
                "quantity": seats,
            }],
        )
        
        return {"message": f"Seat count updated to {seats}"}
        
    except Exception as e:
        logger.error(f"Error updating seats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
