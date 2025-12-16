"""ServiceNow Asset Management API Client.

Implements Asset and Contract management APIs, including hardware/software assets
and contract relationships.

Reference: ServiceNow Zurich REST API
- Asset Management (alm_asset)
- Contract Management (ast_contract)
"""

from typing import Any, Iterator

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class AssetManagementAPIClient(BaseServiceNowClient):
    """ServiceNow Asset Management API Client.
    
    Provides capabilities to:
    - Manage Hardware/Software Assets
    - Manage Contracts
    - Handle Asset-Contract M2M relationships
    - Sync Assets with CIs
    """

    # ========== Asset Management ==========
    
    def get_asset(
        self,
        asset_tag: str | None = None,
        sys_id: str | None = None,
        table: str = "alm_asset",
    ) -> dict[str, Any]:
        """Get an asset by tag or sys_id.
        
        Args:
            asset_tag: Asset tag (e.g., P100045)
            sys_id: Asset sys_id
            table: Asset table (alm_asset, alm_hardware, alm_license)
            
        Returns:
            Asset record
        """
        if sys_id:
            endpoint = f"{self.api_version}/table/{table}/{sys_id}"
            response = self.get(endpoint)
            return response.get("result", {})
        elif asset_tag:
            endpoint = f"{self.api_version}/table/{table}"
            params = {"sysparm_query": f"asset_tag={asset_tag}", "sysparm_limit": 1}
            response = self.get(endpoint, params=params)
            results = response.get("result", [])
            return results[0] if results else {}
        else:
            raise ValueError("Either asset_tag or sys_id required")
    
    def create_hardware_asset(
        self,
        asset_tag: str,
        model: str,
        status:str = "in_stock",
        substatus: str = "available",
        assigned_to: str | None = None,
        location: str | None = None,
        serial_number: str | None = None,
        cost: float | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a hardware asset.
        
        Args:
            asset_tag: Asset tag
            model: Model sys_id
            status: Install status
            substatus: Substatus
            assigned_to: User sys_id
            location: Location sys_id
            serial_number: Serial number
            cost: Cost
            **extra_fields: Additional fields
            
        Returns:
            Created asset record
        """
        data: dict[str, Any] = {
            "asset_tag": asset_tag,
            "model": model,
            "install_status": self._get_status_value(status),
            "substatus": substatus,
        }
        
        if assigned_to:
            data["assigned_to"] = assigned_to
        if location:
            data["location"] = location
        if serial_number:
            data["serial_number"] = serial_number
            data["ci_serial_number"] = serial_number  # Sync to CI
        if cost:
            data["cost"] = cost
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/alm_hardware"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def _get_status_value(self, status: str) -> str:
        """Map generic status strings to ServiceNow values."""
        # This mapping can be expanded based on instance configuration
        status_map = {
            "in_use": "1",
            "in_stock": "6",
            "retired": "7",
            "missing": "8",
        }
        return status_map.get(status, status)

    def update_asset(
        self,
        sys_id: str,
        updates: dict[str, Any],
        table: str = "alm_asset",
    ) -> dict[str, Any]:
        """Update an asset.
        
        Args:
            sys_id: Asset sys_id
            updates: Fields to update
            table: Asset table
            
        Returns:
            Updated asset
        """
        endpoint = f"{self.api_version}/table/{table}/{sys_id}"
        response = self.patch(endpoint, json_data=updates)
        return response.get("result", {})

    # ========== Contract Management ==========
    
    def get_contract(
        self,
        contract_number: str | None = None,
        sys_id: str | None = None,
    ) -> dict[str, Any]:
        """Get a contract.
        
        Args:
            contract_number: Contract number (CTR...)
            sys_id: Contract sys_id
            
        Returns:
            Contract record
        """
        if sys_id:
            endpoint = f"{self.api_version}/table/ast_contract/{sys_id}"
            response = self.get(endpoint)
            return response.get("result", {})
        elif contract_number:
            endpoint = f"{self.api_version}/table/ast_contract"
            params = {"sysparm_query": f"number={contract_number}", "sysparm_limit": 1}
            response = self.get(endpoint, params=params)
            results = response.get("result", [])
            return results[0] if results else {}
        else:
            raise ValueError("Either contract_number or sys_id required")
            
    def create_contract(
        self,
        vendor: str,
        contract_model: str,
        starts: str,
        ends: str,
        number: str | None = None,
        cost: float | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a contract.
        
        Args:
            vendor: Vendor company sys_id
            contract_model: Contract model info
            starts: Start date (YYYY-MM-DD)
            ends: End date (YYYY-MM-DD)
            number: Optional contract number
            cost: Cost
            
        Returns:
            Created contract
        """
        data: dict[str, Any] = {
            "vendor": vendor,
            "contract_model": contract_model,
            "starts": starts,
            "ends": ends,
        }
        
        if number:
            data["vendor_contract"] = number
        if cost:
            data["cost"] = cost
            
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/ast_contract"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
        
    # ========== Asset-Contract Relationships (M2M) ==========
    
    def add_asset_to_contract(
        self,
        contract_sys_id: str,
        asset_sys_id: str,
    ) -> dict[str, Any]:
        """Link an asset to a contract.
        
        Uses clm_m2m_contract_asset table.
        
        Args:
            contract_sys_id: Contract sys_id
            asset_sys_id: Asset sys_id
            
        Returns:
            Created M2M record
        """
        data = {
            "contract": contract_sys_id,
            "asset": asset_sys_id
        }
        
        endpoint = f"{self.api_version}/table/clm_m2m_contract_asset"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def get_assets_by_contract(
        self,
        contract_sys_id: str,
    ) -> list[dict[str, Any]]:
        """Get all assets covered by a contract.
        
        Args:
            contract_sys_id: Contract sys_id
            
        Returns:
            List of M2M records with asset details
        """
        endpoint = f"{self.api_version}/table/clm_m2m_contract_asset"
        params = {
            "sysparm_query": f"contract={contract_sys_id}",
            "sysparm_display_value": "true",
            "sysparm_fields": "sys_id,asset.display_name,asset.asset_tag,asset.serial_number"
        }
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def remove_asset_from_contract(
        self,
        contract_sys_id: str,
        asset_sys_id: str,
    ) -> bool:
        """Remove an asset from a contract.
        
        Args:
            contract_sys_id: Contract sys_id
            asset_sys_id: Asset sys_id
            
        Returns:
            True if removed
        """
        # First find the M2M record
        endpoint = f"{self.api_version}/table/clm_m2m_contract_asset"
        params = {
            "sysparm_query": f"contract={contract_sys_id}^asset={asset_sys_id}",
            "sysparm_limit": 1
        }
        
        response = self.get(endpoint, params=params)
        results = response.get("result", [])
        
        if not results:
            return False
            
        m2m_sys_id = results[0]["sys_id"]
        
        # Delete M2M record
        self.delete(f"{self.api_version}/table/clm_m2m_contract_asset/{m2m_sys_id}")
        return True
