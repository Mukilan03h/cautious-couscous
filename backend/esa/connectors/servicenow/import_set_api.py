"""ServiceNow Import Set API Client.

Implements the ServiceNow Import Set API for bulk data ingestion.
Supports ETL patterns for external data synchronization.

Reference: ServiceNow Zurich REST API - Import Set API
Endpoint: /api/now/import/{tableName}
"""

from typing import Any, Iterator
from dataclasses import dataclass

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class ImportResult:
    """Result of an import set operation."""
    import_set_sys_id: str
    staging_table: str
    status: str
    target_table: str | None
    transform_map: str | None
    records_inserted: int
    records_updated: int
    records_ignored: int
    errors: list[str]
    
    @property
    def success(self) -> bool:
        return self.status in ("complete", "processed") and not self.errors


class ImportSetAPIClient(BaseServiceNowClient):
    """ServiceNow Import Set API Client.
    
    Provides bulk data ingestion capabilities:
    - Insert data into staging (import set) tables
    - Trigger transform maps to target tables
    - Track import status and results
    - Handle coalesce and duplicate detection
    
    Common use cases:
    - CMDB synchronization from external sources
    - Bulk user provisioning
    - Asset inventory imports
    - Integration with ETL tools
    """

    def create_import_set(
        self,
        staging_table: str,
        records: list[dict[str, Any]],
        run_transform: bool = True,
        coalesce_by: list[str] | None = None,
    ) -> ImportResult:
        """Create an import set with records.
        
        Args:
            staging_table: Import set staging table name
            records: List of records to import
            run_transform: Whether to run transform map after insert
            coalesce_by: Fields to use for coalesce (update instead of insert)
            
        Returns:
            ImportResult with status and statistics
        """
        if not records:
            return ImportResult(
                import_set_sys_id="",
                staging_table=staging_table,
                status="empty",
                target_table=None,
                transform_map=None,
                records_inserted=0,
                records_updated=0,
                records_ignored=0,
                errors=["No records provided"],
            )
        
        params: dict[str, Any] = {}
        if not run_transform:
            params["sysparm_skip_transform"] = "true"
        
        endpoint = f"{self.api_version}/import/{staging_table}"
        
        # For single record
        if len(records) == 1:
            response = self.post(endpoint, json_data=records[0], params=params)
        else:
            # Multiple records - use multiInsertResult
            response = self.post(endpoint, json_data={"records": records}, params=params)
        
        return self._parse_import_result(response, staging_table)
    
    def insert_import_set_row(
        self,
        staging_table: str,
        record: dict[str, Any],
        run_transform: bool = True,
    ) -> dict[str, Any]:
        """Insert a single row into an import set table.
        
        Args:
            staging_table: Import set staging table name
            record: Record data to insert
            run_transform: Whether to run transform map
            
        Returns:
            Result with sys_id and transform status
        """
        params: dict[str, Any] = {}
        if not run_transform:
            params["sysparm_skip_transform"] = "true"
        
        endpoint = f"{self.api_version}/import/{staging_table}"
        response = self.post(endpoint, json_data=record, params=params)
        
        return response.get("result", {})
    
    def insert_import_set_rows(
        self,
        staging_table: str,
        records: list[dict[str, Any]],
        run_transform: bool = True,
        batch_size: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Insert multiple rows into an import set table.
        
        Args:
            staging_table: Import set staging table name
            records: List of records to insert
            run_transform: Whether to run transform map
            batch_size: Records per batch
            
        Yields:
            Individual insertion results
        """
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            for record in batch:
                try:
                    result = self.insert_import_set_row(
                        staging_table=staging_table,
                        record=record,
                        run_transform=run_transform,
                    )
                    yield result
                except Exception as e:
                    yield {
                        "error": str(e),
                        "record": record,
                        "status": "error",
                    }
    
    def get_import_set(self, staging_table: str, import_set_sys_id: str) -> dict[str, Any]:
        """Get import set status and details.
        
        Args:
            staging_table: Staging table name
            import_set_sys_id: Import set sys_id
            
        Returns:
            Import set record with status
        """
        endpoint = f"{self.api_version}/table/{staging_table}"
        params = {
            "sysparm_query": f"sys_import_set={import_set_sys_id}",
            "sysparm_limit": 1000,
        }
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def get_import_set_row(
        self,
        staging_table: str,
        row_sys_id: str,
    ) -> dict[str, Any]:
        """Get a specific import set row.
        
        Args:
            staging_table: Staging table name
            row_sys_id: Row sys_id
            
        Returns:
            Import set row data
        """
        endpoint = f"{self.api_version}/table/{staging_table}/{row_sys_id}"
        response = self.get(endpoint)
        return response.get("result", {})
    
    def _parse_import_result(
        self,
        response: dict[str, Any],
        staging_table: str,
    ) -> ImportResult:
        """Parse import set API response."""
        result = response.get("result", {})
        
        # Handle single vs multi-record responses
        if isinstance(result, list):
            results = result
        else:
            results = [result]
        
        inserted = 0
        updated = 0
        ignored = 0
        errors = []
        import_set_sys_id = ""
        target_table = None
        transform_map = None
        
        for r in results:
            import_set_sys_id = r.get("sys_import_set", {}).get("value", "") or import_set_sys_id
            
            status = r.get("status", "").lower()
            if status == "inserted":
                inserted += 1
            elif status == "updated":
                updated += 1
            elif status == "ignored":
                ignored += 1
            elif status == "error":
                errors.append(r.get("status_message", "Unknown error"))
            
            target_table = r.get("target_table") or target_table
            transform_map = r.get("transform_map", {}).get("value") or transform_map
        
        overall_status = "complete" if not errors else "error"
        
        return ImportResult(
            import_set_sys_id=import_set_sys_id,
            staging_table=staging_table,
            status=overall_status,
            target_table=target_table,
            transform_map=transform_map,
            records_inserted=inserted,
            records_updated=updated,
            records_ignored=ignored,
            errors=errors,
        )
    
    # Common import set table helpers
    def import_users(
        self,
        users: list[dict[str, Any]],
        staging_table: str = "u_user_import",
    ) -> ImportResult:
        """Import users via import set.
        
        Standard fields: user_name, first_name, last_name, email, 
                        department, title, manager, active
        """
        return self.create_import_set(staging_table, users)
    
    def import_cmdb_cis(
        self,
        cis: list[dict[str, Any]],
        staging_table: str = "u_cmdb_import",
    ) -> ImportResult:
        """Import CMDB Configuration Items via import set.
        
        Standard fields: name, sys_class_name, serial_number, 
                        manufacturer, ip_address, etc.
        """
        return self.create_import_set(staging_table, cis)
    
    def import_assets(
        self,
        assets: list[dict[str, Any]],
        staging_table: str = "u_asset_import",
    ) -> ImportResult:
        """Import assets via import set.
        
        Standard fields: asset_tag, serial_number, model, 
                        manufacturer, assigned_to, location
        """
        return self.create_import_set(staging_table, assets)


# CMDB Data Ingestion API (specialized for Identification & Reconciliation)
class CMDBIngestionAPIClient(BaseServiceNowClient):
    """ServiceNow CMDB Data Ingestion API Client.
    
    Specialized API for CMDB that uses the Identification and Reconciliation
    Engine (IRE) to prevent duplicate CIs and reconcile attributes.
    
    Endpoint: /api/now/identifyreconcile
    """

    def ingest_cis(
        self,
        items: list[dict[str, Any]],
        data_source: str = "API",
    ) -> dict[str, Any]:
        """Ingest Configuration Items using IRE.
        
        Args:
            items: List of CI data with className and values
            data_source: Data source name for reconciliation
            
        Returns:
            Ingestion result with CI sys_ids
        """
        payload = {
            "items": items,
        }
        
        endpoint = f"{self.api_version}/identifyreconcile"
        response = self.post(endpoint, json_data=payload)
        
        return response.get("result", {})
    
    def ingest_ci(
        self,
        class_name: str,
        values: dict[str, Any],
        relations: list[dict[str, Any]] | None = None,
        related_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ingest a single Configuration Item.
        
        Args:
            class_name: CI class name (e.g., cmdb_ci_server)
            values: CI attribute values
            relations: Optional CI relationships
            related_items: Optional related CI items
            
        Returns:
            Result with CI sys_id and operation performed
        """
        item = {
            "className": class_name,
            "values": values,
        }
        
        if relations:
            item["relations"] = relations
        if related_items:
            item["related_items"] = related_items
        
        return self.ingest_cis([item])
    
    def create_ci_relation(
        self,
        parent_sys_id: str,
        child_sys_id: str,
        relation_type: str = "Depends on::Used by",
    ) -> dict[str, Any]:
        """Create a relationship between two CIs.
        
        Args:
            parent_sys_id: Parent CI sys_id
            child_sys_id: Child CI sys_id
            relation_type: Relationship type name
            
        Returns:
            Relationship record
        """
        # Use table API for relationship creation
        endpoint = f"{self.api_version}/table/cmdb_rel_ci"
        
        data = {
            "parent": parent_sys_id,
            "child": child_sys_id,
            "type": relation_type,
        }
        
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})
