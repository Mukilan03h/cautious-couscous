"""ServiceNow Aggregate API Client.

Implements the ServiceNow Aggregate API for computing statistics on table data.
Useful for dashboards, reporting, and analytics without retrieving all records.

Reference: ServiceNow Zurich REST API - Aggregate API
Endpoint: /api/now/{version}/stats/{tableName}
"""

from typing import Any

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class AggregateAPIClient(BaseServiceNowClient):
    """ServiceNow Aggregate API Client.
    
    Computes aggregate statistics on table data:
    - COUNT: Total record count
    - SUM: Sum of numeric fields
    - AVG: Average of numeric fields
    - MIN: Minimum value
    - MAX: Maximum value
    
    Supports grouping and filtering for complex analytics.
    """

    def get_count(
        self,
        table_name: str,
        query: str | None = None,
    ) -> int:
        """Get total record count for a table.
        
        Args:
            table_name: Name of the table
            query: Optional encoded query filter
            
        Returns:
            Total record count
        """
        params: dict[str, Any] = {
            "sysparm_count": "true",
        }
        
        if query:
            params["sysparm_query"] = query
        
        endpoint = f"{self.api_version}/stats/{table_name}"
        response = self.get(endpoint, params=params)
        
        result = response.get("result", {})
        stats = result.get("stats", {})
        
        return int(stats.get("count", 0))
    
    def get_aggregate(
        self,
        table_name: str,
        aggregate_type: str,
        aggregate_field: str,
        query: str | None = None,
        group_by: str | None = None,
        having: str | None = None,
        display_value: str = "false",
    ) -> dict[str, Any]:
        """Get aggregate statistics for a field.
        
        Args:
            table_name: Name of the table
            aggregate_type: Aggregate type (COUNT, SUM, AVG, MIN, MAX)
            aggregate_field: Field to aggregate
            query: Optional encoded query filter
            group_by: Comma-separated fields to group by
            having: Having clause for grouped results
            display_value: Display value option
            
        Returns:
            Aggregate result with stats
        """
        params: dict[str, Any] = {
            f"sysparm_{aggregate_type.lower()}": aggregate_field,
            "sysparm_display_value": display_value,
        }
        
        if query:
            params["sysparm_query"] = query
        
        if group_by:
            params["sysparm_group_by"] = group_by
        
        if having:
            params["sysparm_having"] = having
        
        endpoint = f"{self.api_version}/stats/{table_name}"
        response = self.get(endpoint, params=params)
        
        return response.get("result", {})
    
    def get_sum(
        self,
        table_name: str,
        field: str,
        query: str | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Get sum of a numeric field.
        
        Args:
            table_name: Name of the table
            field: Numeric field to sum
            query: Optional filter
            group_by: Optional grouping
            
        Returns:
            Sum result
        """
        return self.get_aggregate(
            table_name=table_name,
            aggregate_type="SUM",
            aggregate_field=field,
            query=query,
            group_by=group_by,
        )
    
    def get_avg(
        self,
        table_name: str,
        field: str,
        query: str | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Get average of a numeric field.
        
        Args:
            table_name: Name of the table
            field: Numeric field to average
            query: Optional filter
            group_by: Optional grouping
            
        Returns:
            Average result
        """
        return self.get_aggregate(
            table_name=table_name,
            aggregate_type="AVG",
            aggregate_field=field,
            query=query,
            group_by=group_by,
        )
    
    def get_min_max(
        self,
        table_name: str,
        field: str,
        query: str | None = None,
    ) -> tuple[Any, Any]:
        """Get minimum and maximum values of a field.
        
        Args:
            table_name: Name of the table
            field: Field to analyze
            query: Optional filter
            
        Returns:
            Tuple of (min_value, max_value)
        """
        params: dict[str, Any] = {
            "sysparm_min": field,
            "sysparm_max": field,
        }
        
        if query:
            params["sysparm_query"] = query
        
        endpoint = f"{self.api_version}/stats/{table_name}"
        response = self.get(endpoint, params=params)
        
        result = response.get("result", {})
        stats = result.get("stats", {})
        
        return stats.get("min", {}).get(field), stats.get("max", {}).get(field)
    
    def get_grouped_counts(
        self,
        table_name: str,
        group_by: str,
        query: str | None = None,
        order_by: str | None = None,
        order_dir: str = "desc",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get record counts grouped by field values.
        
        Args:
            table_name: Name of the table
            group_by: Field to group by (can be comma-separated for multiple)
            query: Optional filter
            order_by: Field to order by (default: count)
            order_dir: Order direction (asc/desc)
            limit: Maximum groups to return
            
        Returns:
            List of group results with counts
        """
        params: dict[str, Any] = {
            "sysparm_count": "true",
            "sysparm_group_by": group_by,
            "sysparm_display_value": "true",
        }
        
        if query:
            params["sysparm_query"] = query
        
        if order_by:
            params["sysparm_orderby"] = f"{'DESC' if order_dir == 'desc' else ''}{order_by}"
        
        if limit:
            params["sysparm_top"] = limit
        
        endpoint = f"{self.api_version}/stats/{table_name}"
        response = self.get(endpoint, params=params)
        
        result = response.get("result", [])
        
        # Parse grouped results
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return result.get("groupBy", [])
        
        return []
    
    def get_incident_stats(self, query: str | None = None) -> dict[str, Any]:
        """Get incident statistics summary.
        
        Returns counts grouped by priority, state, and category.
        """
        stats = {
            "total": self.get_count("incident", query),
            "by_priority": self.get_grouped_counts("incident", "priority", query),
            "by_state": self.get_grouped_counts("incident", "state", query),
            "by_category": self.get_grouped_counts("incident", "category", query, limit=10),
        }
        return stats
    
    def get_change_stats(self, query: str | None = None) -> dict[str, Any]:
        """Get change request statistics summary."""
        stats = {
            "total": self.get_count("change_request", query),
            "by_type": self.get_grouped_counts("change_request", "type", query),
            "by_state": self.get_grouped_counts("change_request", "state", query),
            "by_risk": self.get_grouped_counts("change_request", "risk", query),
        }
        return stats
    
    def get_cmdb_stats(self, ci_class: str = "cmdb_ci", query: str | None = None) -> dict[str, Any]:
        """Get CMDB configuration item statistics."""
        stats = {
            "total": self.get_count(ci_class, query),
            "by_class": self.get_grouped_counts(ci_class, "sys_class_name", query, limit=20),
            "by_status": self.get_grouped_counts(ci_class, "operational_status", query),
        }
        return stats
