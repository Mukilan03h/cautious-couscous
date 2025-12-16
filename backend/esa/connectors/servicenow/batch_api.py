"""ServiceNow Batch API Client.

Implements the ServiceNow Batch API for executing multiple REST API calls
in a single HTTP request. Improves performance by up to 40% for bulk operations.

Reference: ServiceNow Zurich REST API - Batch API
Endpoint: /api/now/v1/batch
"""

from typing import Any
from dataclasses import dataclass, field

from esa.connectors.servicenow.base_client import BaseServiceNowClient, ServiceNowAPIError
from esa.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class BatchRequest:
    """Represents a single request in a batch operation."""
    id: str
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    exclude_response_headers: bool = True


@dataclass
class BatchResponse:
    """Represents a single response from a batch operation."""
    id: str
    status_code: int
    status_text: str
    headers: dict[str, str]
    body: dict[str, Any] | None
    error: str | None = None
    
    @property
    def success(self) -> bool:
        """Check if the request was successful."""
        return 200 <= self.status_code < 300


class BatchAPIClient(BaseServiceNowClient):
    """ServiceNow Batch API Client.
    
    Execute multiple REST API calls in a single HTTP request.
    Improves performance for bulk operations by reducing HTTP overhead.
    
    Features:
    - Up to 40% performance improvement
    - Maintains transaction context
    - Individual request error handling
    - Automatic request ID generation
    """

    MAX_BATCH_SIZE = 100  # ServiceNow limit per batch request
    
    def execute_batch(
        self,
        requests: list[BatchRequest],
        rest_requests: bool = True,
    ) -> list[BatchResponse]:
        """Execute a batch of API requests.
        
        Args:
            requests: List of BatchRequest objects
            rest_requests: Whether these are REST requests (default True)
            
        Returns:
            List of BatchResponse objects in same order as requests
        """
        if not requests:
            return []
        
        if len(requests) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {self.MAX_BATCH_SIZE}")
        
        # Build batch request body
        batch_requests = []
        for req in requests:
            batch_item = {
                "id": req.id,
                "method": req.method,
                "url": req.url,
                "headers": req.headers if req.headers else [],
                "exclude_response_headers": req.exclude_response_headers,
            }
            if req.body is not None:
                batch_item["body"] = req.body
            batch_requests.append(batch_item)
        
        payload = {
            "batch_request_payload": {
                "batch_requests": batch_requests
            }
        }
        
        endpoint = "v1/batch"
        response = self.post(endpoint, json_data=payload)
        
        # Parse responses
        serviced_requests = response.get("serviced_requests", [])
        unserviced_requests = response.get("unserviced_requests", [])
        
        # Build response map
        response_map: dict[str, dict[str, Any]] = {}
        for srv in serviced_requests:
            response_map[srv.get("id", "")] = srv
        for unsrv in unserviced_requests:
            response_map[unsrv.get("id", "")] = {
                "id": unsrv.get("id", ""),
                "status_code": 0,
                "status_text": "Unserviced",
                "error_message": unsrv.get("error_message", "Request not serviced"),
            }
        
        # Build ordered response list
        responses = []
        for req in requests:
            resp_data = response_map.get(req.id, {})
            responses.append(BatchResponse(
                id=req.id,
                status_code=resp_data.get("status_code", 0),
                status_text=resp_data.get("status_text", "Unknown"),
                headers=resp_data.get("headers", {}),
                body=resp_data.get("body"),
                error=resp_data.get("error_message"),
            ))
        
        return responses
    
    def batch_get(
        self,
        endpoints: list[str],
        params_list: list[dict[str, Any]] | None = None,
    ) -> list[BatchResponse]:
        """Execute batch GET requests.
        
        Args:
            endpoints: List of API endpoints
            params_list: Optional list of query params for each endpoint
            
        Returns:
            List of BatchResponse objects
        """
        requests = []
        for i, endpoint in enumerate(endpoints):
            url = f"/api/now/{endpoint}"
            
            # Add query params if provided
            if params_list and i < len(params_list):
                params = params_list[i]
                if params:
                    query_string = "&".join(f"{k}={v}" for k, v in params.items())
                    url = f"{url}?{query_string}"
            
            requests.append(BatchRequest(
                id=f"get_{i}",
                method="GET",
                url=url,
            ))
        
        return self.execute_batch(requests)
    
    def batch_create_records(
        self,
        table_name: str,
        records: list[dict[str, Any]],
    ) -> list[BatchResponse]:
        """Create multiple records in a batch.
        
        Args:
            table_name: Target table name
            records: List of record data to create
            
        Returns:
            List of BatchResponse objects with created records
        """
        requests = []
        for i, record in enumerate(records):
            requests.append(BatchRequest(
                id=f"create_{i}",
                method="POST",
                url=f"/api/now/{self.api_version}/table/{table_name}",
                body=record,
            ))
        
        return self.execute_batch(requests)
    
    def batch_update_records(
        self,
        table_name: str,
        updates: list[tuple[str, dict[str, Any]]],
    ) -> list[BatchResponse]:
        """Update multiple records in a batch.
        
        Args:
            table_name: Target table name
            updates: List of (sys_id, update_data) tuples
            
        Returns:
            List of BatchResponse objects with updated records
        """
        requests = []
        for i, (sys_id, data) in enumerate(updates):
            requests.append(BatchRequest(
                id=f"update_{i}",
                method="PATCH",
                url=f"/api/now/{self.api_version}/table/{table_name}/{sys_id}",
                body=data,
            ))
        
        return self.execute_batch(requests)
    
    def batch_delete_records(
        self,
        table_name: str,
        sys_ids: list[str],
    ) -> list[BatchResponse]:
        """Delete multiple records in a batch.
        
        Args:
            table_name: Target table name
            sys_ids: List of sys_ids to delete
            
        Returns:
            List of BatchResponse objects
        """
        requests = []
        for i, sys_id in enumerate(sys_ids):
            requests.append(BatchRequest(
                id=f"delete_{i}",
                method="DELETE",
                url=f"/api/now/{self.api_version}/table/{table_name}/{sys_id}",
            ))
        
        return self.execute_batch(requests)
    
    def batch_get_records(
        self,
        table_name: str,
        sys_ids: list[str],
        fields: str | None = None,
    ) -> list[BatchResponse]:
        """Get multiple records by sys_id in a batch.
        
        Args:
            table_name: Target table name
            sys_ids: List of sys_ids to retrieve
            fields: Optional comma-separated fields to return
            
        Returns:
            List of BatchResponse objects with record data
        """
        requests = []
        for i, sys_id in enumerate(sys_ids):
            url = f"/api/now/{self.api_version}/table/{table_name}/{sys_id}"
            if fields:
                url = f"{url}?sysparm_fields={fields}"
            
            requests.append(BatchRequest(
                id=f"get_{i}",
                method="GET",
                url=url,
            ))
        
        return self.execute_batch(requests)
    
    def batch_execute_chunked(
        self,
        requests: list[BatchRequest],
        chunk_size: int = 50,
    ) -> list[BatchResponse]:
        """Execute a large batch of requests in smaller chunks.
        
        Handles batches larger than MAX_BATCH_SIZE by splitting into chunks.
        
        Args:
            requests: List of all BatchRequest objects
            chunk_size: Size of each chunk (max 100)
            
        Returns:
            Combined list of all BatchResponse objects
        """
        chunk_size = min(chunk_size, self.MAX_BATCH_SIZE)
        
        all_responses = []
        for i in range(0, len(requests), chunk_size):
            chunk = requests[i:i + chunk_size]
            responses = self.execute_batch(chunk)
            all_responses.extend(responses)
        
        return all_responses
