"""ServiceNow Service Catalog API Client.

Implements Service Catalog APIs for ordering items, managing carts,
and tracking requests through the Request -> RITM -> Task hierarchy.

Reference: ServiceNow Zurich REST API
- Service Catalog API: /api/sn_sc/servicecatalog
"""

from typing import Any, Iterator
from dataclasses import dataclass

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class CartItem:
    """Service Catalog cart item."""
    cat_item_id: str
    quantity: int = 1
    variables: dict[str, Any] | None = None


class ServiceCatalogAPIClient(BaseServiceNowClient):
    """ServiceNow Service Catalog API Client.
    
    Provides capabilities to:
    - Browse catalogs, categories, and items
    - Order catalog items and producers
    - Manage shopping cart (add, update, checkout)
    - Track request fulfillment (Request -> RITM -> Task)
    """

    # ========== Catalog Browsing ==========
    
    def get_catalogs(self) -> list[dict[str, Any]]:
        """Get available service catalogs.
        
        Returns:
            List of catalogs
        """
        endpoint = "api/sn_sc/servicecatalog/catalogs"
        response = self.get(endpoint)
        return response.get("result", [])
    
    def get_categories(
        self,
        catalog_id: str | None = None,
        category_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get catalog categories.
        
        Args:
            catalog_id: Filter by catalog sys_id
            category_id: Filter by parent category sys_id
            limit: Record limit
            offset: Record offset
            
        Returns:
            List of categories
        """
        endpoint = "api/sn_sc/servicecatalog/categories"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        
        if catalog_id:
            params["sysparm_catalog"] = catalog_id
        if category_id:
            params["sysparm_category"] = category_id
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def get_items(
        self,
        category_id: str | None = None,
        name: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get catalog items.
        
        Args:
            category_id: Filter by category sys_id
            name: Filter by item name (search)
            limit: Record limit
            offset: Record offset
            
        Returns:
            List of catalog items
        """
        endpoint = "api/sn_sc/servicecatalog/items"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        
        if category_id:
            params["sysparm_category"] = category_id
        if name:
            params["sysparm_text"] = name
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def get_item_details(self, item_sys_id: str) -> dict[str, Any]:
        """Get detailed information about a catalog item.
        
        Args:
            item_sys_id: Catalog item sys_id
            
        Returns:
            Item details including variables
        """
        endpoint = f"api/sn_sc/servicecatalog/items/{item_sys_id}"
        response = self.get(endpoint)
        return response.get("result", {})
    
    # ========== Cart Management & Ordering ==========
    
    def add_to_cart(
        self,
        item_id: str,
        quantity: int = 1,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add an item to the default cart.
        
        Args:
            item_id: Catalog item sys_id
            quantity: Quantity to order
            variables: Item variables/options
            
        Returns:
            Cart item details
        """
        endpoint = "api/sn_sc/servicecatalog/cart/add_item"
        
        data: dict[str, Any] = {
            "sysparm_id": item_id,
            "sysparm_quantity": quantity,
        }
        
        if variables:
            # Format: 'variables': {'var_name': 'value'}
            data["variables"] = variables
        
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})
    
    def checkout_cart(self) -> dict[str, Any]:
        """Checkout the default cart to create a request.
        
        Returns:
            Checkout result (request info)
        """
        endpoint = "api/sn_sc/servicecatalog/cart/checkout"
        response = self.post(endpoint)
        return response.get("result", {})
    
    def submit_producer(
        self,
        producer_id: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit a record producer (e.g., "Report an Issue").
        
        Args:
            producer_id: Record producer sys_id
            variables: Variable values
            
        Returns:
            Created record result
        """
        # Record producers technically use the item submit endpoint
        # but often behave differently (creating Incident/Change instead of Request)
        endpoint = f"api/sn_sc/servicecatalog/items/{producer_id}/submit_producer"
        
        data = {"variables": variables}
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})
    
    def order_item_directly(
        self,
        item_id: str,
        quantity: int = 1,
        variables: dict[str, Any] | None = None,
        requested_for: str | None = None,
    ) -> dict[str, Any]:
        """Order a single item directly (Fast Track).
        
        Bypasses the cart by creating a dedicated cart, adding item, and checking out.
        
        Args:
            item_id: Catalog item sys_id
            quantity: Quantity
            variables: Variables
            requested_for: User sys_id for whom the request is made
            
        Returns:
            Request details
        """
        # This implementation mimics the logic in apireadme.md for "order_catalog_item"
        # 1. Create cart item
        # 2. Submit order
        
        # Determine endpoint based on ServiceNow version/ API availability
        # Using the standard sn_sc API "submit_order" for catalog items
        endpoint = f"api/sn_sc/servicecatalog/items/{item_id}/submit_order"
        
        data: dict[str, Any] = {
            "sysparm_quantity": quantity,
        }
        
        if variables:
            data["variables"] = variables
        if requested_for:
            data["requested_for"] = requested_for
            
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})

    # ========== Request Tracking (Hierarchy) ==========
    
    def get_request_status(self, request_number: str) -> dict[str, Any]:
        """Get full status of a request, including RITMs and Tasks.
        
        Pattern: Request (REQ) -> Requested Item (RITM) -> Catalog Task (SCTASK)
        
        Args:
            request_number: Request number (REQ...)
            
        Returns:
            Nested dictionary with request structure
        """
        # 1. Get Request (REQ)
        req_endpoint = f"{self.api_version}/table/sc_request"
        req_params = {
            "sysparm_query": f"number={request_number}",
            "sysparm_limit": 1
        }
        req_response = self.get(req_endpoint, params=req_params)
        req_result = req_response.get("result", [])
        
        if not req_result:
            return {}
        
        request = req_result[0]
        request_sys_id = request.get("sys_id")
        
        # 2. Get Requested Items (RITM)
        ritm_endpoint = f"{self.api_version}/table/sc_req_item"
        ritm_params = {
            "sysparm_query": f"request={request_sys_id}",
            "sysparm_display_value": "true"
        }
        ritm_response = self.get(ritm_endpoint, params=ritm_params)
        ritms = ritm_response.get("result", [])
        
        # 3. Get Catalog Tasks (SCTASK) for each RITM
        task_endpoint = f"{self.api_version}/table/sc_task"
        
        for ritm in ritms:
            ritm_sys_id = ritm.get("sys_id")
            task_params = {
                "sysparm_query": f"request_item={ritm_sys_id}",
                "sysparm_display_value": "true"
            }
            task_response = self.get(task_endpoint, params=task_params)
            ritm["tasks"] = task_response.get("result", [])
            
        request["items"] = ritms
        return request
