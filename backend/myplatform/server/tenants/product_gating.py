"""
Product gating for enterprise features.
Ported from ee/esa/server/tenants/product_gating.py
"""
from typing import Optional

from esa.utils.logger import setup_logger
from myplatform.server.tenants.billing import fetch_billing_information
from myplatform.server.tenants.models import BillingInformation

logger = setup_logger()


class ProductGating:
    """
    Checks whether features should be gated based on subscription.
    
    For the free platform, all features are enabled.
    """
    
    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self._billing_info: Optional[BillingInformation] = None
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled for the tenant.
        
        For the free platform, all features are enabled.
        """
        # Free platform - all features enabled
        return True
    
    def get_feature_limit(self, feature_name: str) -> Optional[int]:
        """
        Get the limit for a feature.
        
        Returns None for unlimited.
        """
        # Free platform - no limits
        return None
    
    def is_subscribed(self) -> bool:
        """Check if the tenant has an active subscription."""
        if not self.tenant_id:
            return True  # Free platform
        
        try:
            billing = fetch_billing_information(self.tenant_id)
            if isinstance(billing, BillingInformation):
                return billing.status == "active"
            return False
        except Exception:
            return True  # Default to enabled for free platform
    
    def check_seat_limit(self, current_seats: int, requested_seats: int) -> bool:
        """Check if adding seats is allowed."""
        # Free platform - unlimited seats
        return True


# Feature flags - all enabled for free platform
FEATURE_FLAGS = {
    "analytics": True,
    "user_groups": True,
    "sso": True,
    "custom_branding": True,
    "api_access": True,
    "advanced_permissions": True,
    "query_history": True,
    "usage_reports": True,
    "multi_tenant": True,
    "custom_connectors": True,
}


def is_feature_gated(feature_name: str, tenant_id: Optional[str] = None) -> bool:
    """
    Check if a feature is gated (disabled) for a tenant.
    
    For the free platform, no features are gated.
    """
    return False  # All features enabled


def get_gated_features(tenant_id: Optional[str] = None) -> list[str]:
    """
    Get list of gated features for a tenant.
    
    For the free platform, empty list.
    """
    return []  # No gated features


def check_feature_access(
    feature_name: str,
    tenant_id: Optional[str] = None,
    raise_on_gated: bool = True,
) -> bool:
    """
    Check if a feature is accessible.
    
    For the free platform, always returns True.
    """
    return True  # All features accessible
