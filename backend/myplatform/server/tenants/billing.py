"""
Tenant billing operations for MyPlatform.
Ported from ee/esa/server/tenants/billing.py
"""
from typing import cast

import stripe

from myplatform.configs.app_configs import STRIPE_PRICE_ID, STRIPE_SECRET_KEY
from myplatform.server.tenants.access import generate_data_plane_token
from myplatform.server.tenants.models import BillingInformation, SubscriptionStatusResponse
from esa.configs.app_configs import CONTROL_PLANE_API_BASE_URL
from esa.utils.logger import setup_logger

stripe.api_key = STRIPE_SECRET_KEY

logger = setup_logger()


def fetch_stripe_checkout_session(tenant_id: str) -> str:
    """Create a Stripe checkout session for a tenant."""
    import requests
    
    token = generate_data_plane_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{CONTROL_PLANE_API_BASE_URL}/create-checkout-session"
    params = {"tenant_id": tenant_id}
    response = requests.post(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["sessionId"]


def fetch_tenant_stripe_information(tenant_id: str) -> dict:
    """Fetch Stripe information for a tenant."""
    import requests
    
    token = generate_data_plane_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{CONTROL_PLANE_API_BASE_URL}/tenant-stripe-information"
    params = {"tenant_id": tenant_id}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def fetch_billing_information(
    tenant_id: str,
) -> BillingInformation | SubscriptionStatusResponse:
    """Fetch billing information for a tenant."""
    import requests
    
    logger.info("Fetching billing information")
    token = generate_data_plane_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{CONTROL_PLANE_API_BASE_URL}/billing-information"
    params = {"tenant_id": tenant_id}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    response_data = response.json()

    # Check if the response indicates no subscription
    if (
        isinstance(response_data, dict)
        and "subscribed" in response_data
        and not response_data["subscribed"]
    ):
        return SubscriptionStatusResponse(**response_data)

    # Otherwise, parse as BillingInformation
    return BillingInformation(**response_data)


def register_tenant_users(tenant_id: str, number_of_users: int) -> stripe.Subscription:
    """
    Send a request to the control service to register the number of users for a tenant.
    """
    if not STRIPE_PRICE_ID:
        raise Exception("STRIPE_PRICE_ID is not set")

    response = fetch_tenant_stripe_information(tenant_id)
    stripe_subscription_id = cast(str, response.get("stripe_subscription_id"))

    subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    updated_subscription = stripe.Subscription.modify(
        stripe_subscription_id,
        items=[
            {
                "id": subscription["items"]["data"][0].id,
                "price": STRIPE_PRICE_ID,
                "quantity": number_of_users,
            }
        ],
        metadata={"tenant_id": str(tenant_id)},
    )
    return updated_subscription
