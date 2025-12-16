"""ServiceNow CMDB API Client.

Comprehensive CMDB (Configuration Management Database) API implementation
supporting the full CI lifecycle, meta data, and relationships.

Reference: ServiceNow Zurich REST API - CMDB APIs
- CMDB Instance API: /api/now/cmdb/instance/{className}
- CMDB Meta API: /api/now/cmdb/meta/{className}
- CI Lifecycle Management API: /api/sn_cmdb_ws/v1/lifecycle
"""

from typing import Any, Iterator
from dataclasses import dataclass

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class CIClass:
    """CMDB CI Class metadata."""
    name: str
    label: str
    parent: str | None
    attributes: list[dict[str, Any]]
    is_extendable: bool
    icon: str | None


class CMDBAPIClient(BaseServiceNowClient):
    """ServiceNow CMDB API Client.
    
    Provides comprehensive CMDB management:
    - CI Instance CRUD operations
    - Class metadata and schema discovery
    - CI relationships management
    - CI lifecycle state management
    - CI actions execution
    """

    # Common CI class names
    CI_CLASSES = {
        "base": "cmdb_ci",
        "server": "cmdb_ci_server",
        "vm": "cmdb_ci_vm_instance",
        "computer": "cmdb_ci_computer",
        "application": "cmdb_ci_appl",
        "service": "cmdb_ci_service",
        "database": "cmdb_ci_db_instance",
        "hardware": "cmdb_ci_hardware",
        "network": "cmdb_ci_netgear",
        "storage": "cmdb_ci_storage_device",
        "cloud_service": "cmdb_ci_cloud_service_account",
        "container": "cmdb_ci_container",
        "kubernetes": "cmdb_ci_kubernetes_cluster",
    }

    # Common relationship types
    RELATION_TYPES = {
        "depends_on": "Depends on::Used by",
        "runs_on": "Runs on::Runs",
        "hosted_on": "Hosted on::Hosts",
        "connects_to": "Connects to::Connected by",
        "contains": "Contains::Contained by",
        "provided_by": "Provided by::Provides",
        "managed_by": "Managed by::Manages",
        "owned_by": "Owned by::Owns",
        "virtualized_by": "Virtualized by::Virtualizes",
        "cluster_of": "Cluster of::Cluster is",
    }

    # ========== CMDB Instance API ==========
    
    def get_ci(
        self,
        class_name: str,
        sys_id: str,
        fields: str | None = None,
    ) -> dict[str, Any]:
        """Get a specific Configuration Item.
        
        Args:
            class_name: CI class name (e.g., cmdb_ci_server)
            sys_id: CI sys_id
            fields: Comma-separated field names to return
            
        Returns:
            CI record data
        """
        params: dict[str, Any] = {}
        if fields:
            params["sysparm_fields"] = fields
        
        endpoint = f"{self.api_version}/cmdb/instance/{class_name}/{sys_id}"
        response = self.get(endpoint, params=params)
        
        return response.get("result", {})
    
    def get_cis(
        self,
        class_name: str,
        query: str | None = None,
        fields: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "sys_updated_on",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Get Configuration Items by class.
        
        Args:
            class_name: CI class name
            query: Encoded query filter
            fields: Fields to return
            limit: Maximum records
            offset: Starting offset
            order_by: Field to order by
            order_dir: Order direction
            
        Returns:
            Tuple of (CI records list, total count or None)
        """
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        
        if fields:
            params["sysparm_fields"] = fields
        
        # Build query with ordering
        query_parts = []
        if query:
            query_parts.append(query)
        order_prefix = "ORDERBYDESC" if order_dir == "desc" else "ORDERBY"
        query_parts.append(f"{order_prefix}{order_by}")
        params["sysparm_query"] = "^".join(query_parts)
        
        endpoint = f"{self.api_version}/cmdb/instance/{class_name}"
        response = self.get(endpoint, params=params)
        
        result = response.get("result", {})
        records = result if isinstance(result, list) else result.get("records", [])
        
        return records, None
    
    def get_cis_paginated(
        self,
        class_name: str,
        query: str | None = None,
        fields: str | None = None,
        limit: int = 100,
        max_records: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Iterate through all CIs with automatic pagination.
        
        Args:
            class_name: CI class name
            query: Optional filter
            fields: Fields to return
            limit: Page size
            max_records: Maximum total records
            
        Yields:
            Individual CI records
        """
        offset = 0
        count = 0
        
        while True:
            records, _ = self.get_cis(
                class_name=class_name,
                query=query,
                fields=fields,
                limit=limit,
                offset=offset,
            )
            
            if not records:
                break
            
            for record in records:
                yield record
                count += 1
                if max_records and count >= max_records:
                    return
            
            if len(records) < limit:
                break
            
            offset += limit
    
    def create_ci(
        self,
        class_name: str,
        data: dict[str, Any],
        source: str = "API",
    ) -> dict[str, Any]:
        """Create a new Configuration Item.
        
        Args:
            class_name: CI class name
            data: CI attribute values
            source: Data source for reconciliation
            
        Returns:
            Created CI record
        """
        endpoint = f"{self.api_version}/cmdb/instance/{class_name}"
        
        payload = {
            "attributes": data,
            "source": source,
        }
        
        response = self.post(endpoint, json_data=payload)
        return response.get("result", {})
    
    def update_ci(
        self,
        class_name: str,
        sys_id: str,
        data: dict[str, Any],
        source: str = "API",
    ) -> dict[str, Any]:
        """Update a Configuration Item.
        
        Args:
            class_name: CI class name
            sys_id: CI sys_id
            data: Attributes to update
            source: Data source
            
        Returns:
            Updated CI record
        """
        endpoint = f"{self.api_version}/cmdb/instance/{class_name}/{sys_id}"
        
        payload = {
            "attributes": data,
            "source": source,
        }
        
        response = self.patch(endpoint, json_data=payload)
        return response.get("result", {})
    
    def delete_ci(self, class_name: str, sys_id: str) -> bool:
        """Delete a Configuration Item.
        
        Args:
            class_name: CI class name
            sys_id: CI sys_id
            
        Returns:
            True if deleted
        """
        endpoint = f"{self.api_version}/cmdb/instance/{class_name}/{sys_id}"
        self.delete(endpoint)
        return True
    
    # ========== CMDB Meta API ==========
    
    def get_class_metadata(self, class_name: str) -> CIClass:
        """Get metadata for a CI class.
        
        Args:
            class_name: CI class name
            
        Returns:
            CIClass with schema information
        """
        endpoint = f"{self.api_version}/cmdb/meta/{class_name}"
        response = self.get(endpoint)
        
        result = response.get("result", {})
        
        return CIClass(
            name=class_name,
            label=result.get("label", class_name),
            parent=result.get("parent"),
            attributes=result.get("attributes", []),
            is_extendable=result.get("is_extendable", False),
            icon=result.get("icon"),
        )
    
    def get_class_attributes(self, class_name: str) -> list[dict[str, Any]]:
        """Get all attributes for a CI class.
        
        Args:
            class_name: CI class name
            
        Returns:
            List of attribute definitions
        """
        metadata = self.get_class_metadata(class_name)
        return metadata.attributes
    
    def get_class_hierarchy(self, class_name: str = "cmdb_ci") -> dict[str, Any]:
        """Get the class hierarchy starting from a class.
        
        Args:
            class_name: Starting class name
            
        Returns:
            Hierarchical class structure
        """
        endpoint = f"{self.api_version}/cmdb/meta/{class_name}/hierarchy"
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_child_classes(self, class_name: str) -> list[str]:
        """Get direct child classes of a CI class.
        
        Args:
            class_name: Parent class name
            
        Returns:
            List of child class names
        """
        endpoint = f"{self.api_version}/table/sys_db_object"
        params = {
            "sysparm_query": f"super_class.name={class_name}",
            "sysparm_fields": "name,label",
        }
        
        response = self.get(endpoint, params=params)
        result = response.get("result", [])
        
        return [r.get("name") for r in result if r.get("name")]
    
    # ========== CI Relationships ==========
    
    def get_ci_relationships(
        self,
        sys_id: str,
        direction: str = "both",
        depth: int = 1,
    ) -> dict[str, Any]:
        """Get relationships for a CI.
        
        Args:
            sys_id: CI sys_id
            direction: Relationship direction (parent, child, both)
            depth: Traversal depth
            
        Returns:
            Relationship data with related CIs
        """
        endpoint = f"{self.api_version}/table/cmdb_rel_ci"
        
        if direction == "parent":
            query = f"child={sys_id}"
        elif direction == "child":
            query = f"parent={sys_id}"
        else:
            query = f"parent={sys_id}^ORchild={sys_id}"
        
        params = {
            "sysparm_query": query,
            "sysparm_display_value": "true",
        }
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def create_ci_relationship(
        self,
        parent_sys_id: str,
        child_sys_id: str,
        relation_type: str,
        connection_strength: str = "Always",
    ) -> dict[str, Any]:
        """Create a relationship between two CIs.
        
        Args:
            parent_sys_id: Parent CI sys_id
            child_sys_id: Child CI sys_id
            relation_type: Relationship type name or sys_id
            connection_strength: Strength (Always, Often, Sometimes)
            
        Returns:
            Created relationship record
        """
        endpoint = f"{self.api_version}/table/cmdb_rel_ci"
        
        data = {
            "parent": parent_sys_id,
            "child": child_sys_id,
            "type": relation_type,
            "connection_strength": connection_strength,
        }
        
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})
    
    def delete_ci_relationship(self, relationship_sys_id: str) -> bool:
        """Delete a CI relationship.
        
        Args:
            relationship_sys_id: Relationship record sys_id
            
        Returns:
            True if deleted
        """
        endpoint = f"{self.api_version}/table/cmdb_rel_ci/{relationship_sys_id}"
        self.delete(endpoint)
        return True
    
    # ========== CI Lifecycle Management API ==========
    
    def set_ci_operational_status(
        self,
        sys_id: str,
        operational_status: int | str,
    ) -> dict[str, Any]:
        """Set CI operational status.
        
        Status values:
        - 1: Operational
        - 2: Non-Operational
        - 3: Repair in Progress
        - 4: DR Standby
        - 5: Ready
        - 6: Retired
        
        Args:
            sys_id: CI sys_id
            operational_status: Status value or name
            
        Returns:
            Updated CI record
        """
        # Use Table API for direct update
        endpoint = f"{self.api_version}/table/cmdb_ci/{sys_id}"
        
        data = {"operational_status": str(operational_status)}
        response = self.patch(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def set_ci_install_status(
        self,
        sys_id: str,
        install_status: int | str,
    ) -> dict[str, Any]:
        """Set CI install status.
        
        Status values:
        - 1: Installed
        - 2: On Order
        - 3: In Maintenance
        - 4: Pending Install
        - 5: Pending Repair
        - 6: In Stock
        - 7: Retired
        - 8: Stolen
        
        Args:
            sys_id: CI sys_id
            install_status: Status value
            
        Returns:
            Updated CI record
        """
        endpoint = f"{self.api_version}/table/cmdb_ci/{sys_id}"
        
        data = {"install_status": str(install_status)}
        response = self.patch(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def retire_ci(self, sys_id: str, reason: str | None = None) -> dict[str, Any]:
        """Retire a Configuration Item.
        
        Args:
            sys_id: CI sys_id
            reason: Retirement reason
            
        Returns:
            Updated CI record
        """
        data: dict[str, Any] = {
            "install_status": "7",  # Retired
            "operational_status": "6",  # Retired
        }
        
        if reason:
            data["short_description"] = f"[RETIRED] {reason}"
        
        endpoint = f"{self.api_version}/table/cmdb_ci/{sys_id}"
        response = self.patch(endpoint, json_data=data)
        
        return response.get("result", {})
    
    # ========== Convenience Methods ==========
    
    def get_servers(
        self,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get server CIs."""
        records, _ = self.get_cis("cmdb_ci_server", query=query, limit=limit)
        return records
    
    def get_applications(
        self,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get application CIs."""
        records, _ = self.get_cis("cmdb_ci_appl", query=query, limit=limit)
        return records
    
    def get_services(
        self,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get service CIs."""
        records, _ = self.get_cis("cmdb_ci_service", query=query, limit=limit)
        return records
    
    def get_databases(
        self,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get database CIs."""
        records, _ = self.get_cis("cmdb_ci_db_instance", query=query, limit=limit)
        return records
    
    def search_cis(
        self,
        search_term: str,
        class_name: str = "cmdb_ci",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search CIs by name or description.
        
        Args:
            search_term: Search text
            class_name: CI class to search
            limit: Maximum results
            
        Returns:
            Matching CI records
        """
        query = f"nameLIKE{search_term}^ORshort_descriptionLIKE{search_term}"
        records, _ = self.get_cis(class_name, query=query, limit=limit)
        return records
