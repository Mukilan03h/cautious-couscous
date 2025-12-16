"""ServiceNow REST API Client.

Implements the ServiceNow Table API (v2) following the official Zurich API specification.
Supports both Basic Authentication and OAuth 2.0 for secure access.

Reference: ServiceNow Zurich REST API Documentation
"""

import time
from typing import Any
from urllib.parse import quote

import requests
from requests.exceptions import HTTPError

from esa.connectors.cross_connector_utils.rate_limit_wrapper import rate_limit_builder
from esa.utils.retry_wrapper import retry_builder
from esa.utils.logger import setup_logger

logger = setup_logger()

# API version to use - explicitly specified per Zurich docs to avoid breaking changes
API_VERSION = "v2"


class ServiceNowAPIError(Exception):
    """Base exception for ServiceNow API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ServiceNowAuthError(ServiceNowAPIError):
    """Authentication failed (401)."""
    pass


class ServiceNowPermissionError(ServiceNowAPIError):
    """Insufficient permissions (403)."""
    pass


class ServiceNowNotFoundError(ServiceNowAPIError):
    """Resource not found (404)."""
    pass


class ServiceNowRateLimitError(ServiceNowAPIError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, 429)
        self.retry_after = retry_after


class ServiceNowClient:
    """ServiceNow REST API Client implementing Table API v2.
    
    Follows the official ServiceNow Zurich API specification with:
    - Versioned URI structure: /api/now/{version}/table/{tableName}
    - Proper Accept/Content-Type headers (application/json)
    - Query parameters for filtering, pagination, and field selection
    - Rate limiting with Retry-After header support
    - OAuth 2.0 and Basic Authentication
    """

    # Table configurations with field mappings
    # Per Zurich docs: use sysparm_fields to limit response payload
    TABLE_CONFIG: dict[str, dict[str, str]] = {
        # ITSM Core Tables
        "incident": {
            "fields": "sys_id,number,short_description,description,state,priority,urgency,impact,category,subcategory,assigned_to,opened_by,caller_id,opened_at,resolved_at,closed_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "problem": {
            "fields": "sys_id,number,short_description,description,state,priority,category,assigned_to,opened_by,opened_at,resolved_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "change_request": {
            "fields": "sys_id,number,short_description,description,state,type,risk,impact,category,assigned_to,requested_by,opened_at,start_date,end_date,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_request": {
            "fields": "sys_id,number,short_description,description,request_state,requested_for,opened_by,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_req_item": {
            "fields": "sys_id,number,short_description,description,state,cat_item,request,quantity,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,request_item,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,opened_by,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        # Knowledge Management
        "kb_knowledge": {
            "fields": "sys_id,number,short_description,text,author,kb_knowledge_base,kb_category,workflow_state,published,sys_created_on,sys_updated_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "kb_category": {
            "fields": "sys_id,label,description,parent,sys_updated_on",
            "display_field": "label",
            "order_by": "sys_updated_on",
        },
        # CMDB Tables
        "cmdb_ci": {
            "fields": "sys_id,name,short_description,sys_class_name,operational_status,install_status,manufacturer,vendor,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_server": {
            "fields": "sys_id,name,short_description,ip_address,os,os_version,manufacturer,model_id,serial_number,cpu_count,ram,disk_space,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_computer": {
            "fields": "sys_id,name,short_description,ip_address,os,os_version,manufacturer,model_id,serial_number,cpu_type,ram,disk_space,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_appl": {
            "fields": "sys_id,name,short_description,version,vendor,install_status,operational_status,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_service": {
            "fields": "sys_id,name,short_description,service_classification,operational_status,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_hardware": {
            "fields": "sys_id,name,short_description,asset_tag,serial_number,manufacturer,model_id,install_status,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_rel_ci": {
            "fields": "sys_id,parent,child,type,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        # Customer Service Management (CSM)
        "sn_customerservice_case": {
            "fields": "sys_id,number,short_description,description,state,priority,contact,account,opened_at,closed_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "customer_contact": {
            "fields": "sys_id,name,first_name,last_name,email,phone,account,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "customer_account": {
            "fields": "sys_id,name,account_code,industry,street,city,state,country,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        # HR Service Delivery (HRSD)
        "sn_hr_core_case": {
            "fields": "sys_id,number,short_description,description,state,hr_service,opened_for,opened_by,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sn_hr_core_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,parent,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        # Service Catalog
        "sc_cat_item": {
            "fields": "sys_id,name,short_description,description,category,active,price,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "sc_category": {
            "fields": "sys_id,title,description,parent,active,sys_updated_on",
            "display_field": "title",
            "order_by": "sys_updated_on",
        },
        # Security Operations
        "sn_si_incident": {
            "fields": "sys_id,number,short_description,description,state,severity,priority,category,assigned_to,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sn_vul_vulnerable_item": {
            "fields": "sys_id,vulnerability,cmdb_ci,risk_score,state,first_found,last_found,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        # Users and Groups
        "sys_user": {
            "fields": "sys_id,user_name,name,first_name,last_name,email,title,department,manager,active,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "sys_user_group": {
            "fields": "sys_id,name,description,manager,email,active,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
    }

    def __init__(
        self,
        instance_url: str,
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        calls_per_minute: int | None = None,
    ):
        """Initialize ServiceNow client.
        
        Args:
            instance_url: ServiceNow instance URL (e.g., 'mycompany' or 'mycompany.service-now.com')
            username: Service account username
            password: Service account password
            client_id: OAuth 2.0 client ID (optional, for OAuth auth)
            client_secret: OAuth 2.0 client secret (optional, for OAuth auth)
            calls_per_minute: Rate limit (optional)
        """
        # Normalize instance URL per Zurich docs format
        self.instance_url = self._normalize_instance_url(instance_url)
        self.base_url = f"{self.instance_url}/api/now/{API_VERSION}"
        
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        
        # OAuth token management
        self._access_token: str | None = None
        self._token_expiry: float = 0
        
        # Setup rate-limited request function
        self._setup_request_function(calls_per_minute)
    
    def _normalize_instance_url(self, url: str) -> str:
        """Normalize instance URL to standard format."""
        url = url.strip().rstrip("/")
        
        # Remove protocol if present
        if url.startswith("https://"):
            url = url[8:]
        elif url.startswith("http://"):
            url = url[7:]
        
        # Add .service-now.com if not present
        if ".service-now.com" not in url:
            url = f"{url}.service-now.com"
        
        return f"https://{url}"
    
    def _get_oauth_token(self) -> str:
        """Get OAuth 2.0 access token using Resource Owner Password Credentials grant.
        
        Per Zurich docs: OAuth 2.0 token-based authentication is the recommended method
        for production integrations.
        """
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        
        if not self.client_id or not self.client_secret:
            raise ServiceNowAuthError("OAuth credentials (client_id, client_secret) required")
        
        token_url = f"{self.instance_url}/oauth_token.do"
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            self._access_token = token_data["access_token"]
            # Set expiry with 60 second buffer
            expires_in = token_data.get("expires_in", 1800)
            self._token_expiry = time.time() + expires_in - 60
            
            logger.info("ServiceNow OAuth token acquired successfully")
            return self._access_token
            
        except HTTPError as e:
            raise ServiceNowAuthError(f"OAuth token request failed: {e}") from e
    
    def _setup_request_function(self, max_calls_per_minute: int | None) -> None:
        """Setup the rate-limited request function with retry logic."""
        
        @retry_builder(tries=3, delay=1, backoff=2)
        @(
            rate_limit_builder(max_calls=max_calls_per_minute, period=60)
            if max_calls_per_minute
            else lambda x: x
        )
        def make_request_inner(
            endpoint: str,
            params: dict[str, Any] | None = None,
            method: str = "GET",
        ) -> dict[str, Any]:
            """Execute HTTP request to ServiceNow API.
            
            Per Zurich docs: Accept and Content-Type headers are MANDATORY
            for requests with bodies or expecting JSON responses.
            """
            url = f"{self.base_url}/{endpoint}"
            
            # Headers per Zurich docs - mandatory for JSON responses
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            
            # Determine authentication method
            auth = None
            if self.client_id and self.client_secret:
                # OAuth 2.0
                headers["Authorization"] = f"Bearer {self._get_oauth_token()}"
            elif self.username and self.password:
                # Basic Authentication
                auth = (self.username, self.password)
            else:
                raise ServiceNowAuthError("No authentication credentials configured")
            
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    auth=auth,
                    headers=headers,
                    params=params or {},
                    timeout=60,
                )
                
                # Handle rate limiting per Zurich docs
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited by ServiceNow, waiting {retry_after}s")
                    time.sleep(retry_after)
                    # Retry after waiting
                    response = requests.request(
                        method=method,
                        url=url,
                        auth=auth,
                        headers=headers,
                        params=params or {},
                        timeout=60,
                    )
                
                # Handle error responses per Zurich docs
                if response.status_code == 401:
                    # Clear OAuth token on auth failure
                    self._access_token = None
                    self._token_expiry = 0
                    raise ServiceNowAuthError("Authentication failed (401)")
                elif response.status_code == 403:
                    raise ServiceNowPermissionError(
                        f"Insufficient permissions to access {endpoint} (403)"
                    )
                elif response.status_code == 404:
                    raise ServiceNowNotFoundError(f"Resource not found: {endpoint} (404)")
                elif response.status_code == 400:
                    error_msg = response.text[:500] if response.text else "Bad request"
                    raise ServiceNowAPIError(f"Bad request (400): {error_msg}", 400)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                raise ServiceNowAPIError(f"Request timeout: {e}") from e
            except requests.exceptions.ConnectionError as e:
                raise ServiceNowAPIError(f"Connection error: {e}") from e
        
        self._make_request = make_request_inner
    
    def fetch_table_records(
        self,
        table_name: str,
        offset: int = 0,
        limit: int = 100,
        updated_after: float | None = None,
        custom_query: str | None = None,
        fields: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch records from a ServiceNow table using Table API.
        
        Per Zurich docs (Table API Query Parameters):
        - sysparm_query: Encoded query string with ^ for AND, ^OR for OR
        - sysparm_limit: Max records to return (default 10,000)
        - sysparm_offset: Starting record index for pagination
        - sysparm_fields: Comma-separated field names to return
        - displayvalue=all: Return both sys values and display values (dv_ prefix)
        
        Args:
            table_name: ServiceNow table name (e.g., 'incident')
            offset: Starting record index
            limit: Maximum records to return
            updated_after: Unix timestamp to filter by sys_updated_on
            custom_query: Additional query conditions
            fields: Override default fields
            
        Returns:
            Tuple of (records list, has_more boolean)
        """
        # Get table config or use defaults
        config = self.TABLE_CONFIG.get(table_name, {})
        default_fields = config.get(
            "fields", 
            "sys_id,number,short_description,description,sys_updated_on"
        )
        order_by = config.get("order_by", "sys_updated_on")
        
        # Build query parameters per Zurich docs
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_fields": fields or default_fields,
            "displayvalue": "all",  # Get both system and display values
        }
        
        # Build sysparm_query with proper encoding per Zurich docs
        query_parts = []
        
        # Add updated_after filter using proper operator syntax
        if updated_after:
            # Convert to ServiceNow datetime format
            dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(updated_after))
            # Use > operator per Zurich docs operator table
            query_parts.append(f"sys_updated_on>{dt_str}")
        
        # Add custom query conditions
        if custom_query:
            query_parts.append(custom_query)
        
        # Add ordering
        query_parts.append(f"ORDERBY{order_by}")
        
        if query_parts:
            # Join with ^ for AND per Zurich docs
            params["sysparm_query"] = "^".join(query_parts)
        
        # Make request
        endpoint = f"table/{table_name}"
        data = self._make_request(endpoint, params)
        
        result = data.get("result", [])
        has_more = len(result) == limit
        
        return result, has_more
    
    def fetch_knowledge_articles(
        self,
        offset: int = 0,
        limit: int = 100,
        updated_after: float | None = None,
        published_only: bool = True,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch knowledge articles.
        
        Uses kb_knowledge table with optional filter for published articles.
        """
        custom_query = "workflow_state=published" if published_only else None
        return self.fetch_table_records(
            table_name="kb_knowledge",
            offset=offset,
            limit=limit,
            updated_after=updated_after,
            custom_query=custom_query,
        )
    
    def fetch_cmdb_records(
        self,
        ci_class: str = "cmdb_ci",
        offset: int = 0,
        limit: int = 100,
        updated_after: float | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch CMDB Configuration Items.
        
        Per Zurich docs: Use INSTANCEOF operator for extended table queries.
        """
        # For base cmdb_ci, we might want to use INSTANCEOF to get all subtypes
        if ci_class == "cmdb_ci":
            # Get all CI types that extend cmdb_ci
            custom_query = None  # Base table gets all records
        else:
            custom_query = None
        
        return self.fetch_table_records(
            table_name=ci_class,
            offset=offset,
            limit=limit,
            updated_after=updated_after,
            custom_query=custom_query,
        )
    
    def build_record_url(self, table_name: str, sys_id: str) -> str:
        """Build a URL to view a record in the ServiceNow UI.
        
        Uses the standard nav_to.do navigation endpoint.
        """
        return f"{self.instance_url}/nav_to.do?uri={table_name}.do%3Fsys_id%3D{sys_id}"
    
    def validate_connection(self) -> bool:
        """Validate that the connection is working.
        
        Attempts to fetch a single incident record to verify:
        1. Authentication is successful
        2. User has read permissions on the incident table
        """
        try:
            self.fetch_table_records("incident", limit=1)
            return True
        except ServiceNowAPIError:
            return False
