"""ServiceNow Base API Client.

Provides the foundation for all ServiceNow API clients with:
- Authentication (OAuth 2.0, Basic Auth)
- Rate limiting with exponential backoff
- Error handling and retry logic
- Session management and connection pooling

Reference: ServiceNow Zurich REST API Documentation
"""

import time
from abc import ABC
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from esa.utils.logger import setup_logger

logger = setup_logger()

# API version - Zurich release
API_VERSION = "v2"

# Default timeouts (seconds)
DEFAULT_TIMEOUT = 60
DEFAULT_CONNECT_TIMEOUT = 10

# Rate limiting defaults (per Zurich docs: 1,800-7,200 requests/hour/user)
DEFAULT_RATE_LIMIT = 30  # requests per minute (conservative)


class ServiceNowAPIError(Exception):
    """Base exception for ServiceNow API errors."""

    def __init__(
        self, 
        message: str, 
        status_code: int | None = None,
        error_detail: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_detail = error_detail or {}


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


class ServiceNowConflictError(ServiceNowAPIError):
    """Conflict error (409) - typically during concurrent updates."""
    pass


class ServiceNowValidationError(ServiceNowAPIError):
    """Validation error (400) - bad request or invalid data."""
    pass


class ServiceNowServerError(ServiceNowAPIError):
    """Server error (5xx)."""
    pass


class BaseServiceNowClient(ABC):
    """Base client for all ServiceNow API interactions.
    
    Provides common functionality:
    - Session management with connection pooling
    - OAuth 2.0 and Basic Authentication
    - Retry logic with exponential backoff
    - Rate limiting
    - Comprehensive error handling
    """

    def __init__(
        self,
        instance_url: str,
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_version: str = API_VERSION,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        calls_per_minute: int = DEFAULT_RATE_LIMIT,
    ):
        """Initialize base ServiceNow client.
        
        Args:
            instance_url: ServiceNow instance URL or subdomain
            username: Service account username
            password: Service account password
            client_id: OAuth 2.0 client ID (optional)
            client_secret: OAuth 2.0 client secret (optional)
            api_version: API version to use (default: v2)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            calls_per_minute: Rate limit in requests per minute
        """
        self.instance_url = self._normalize_instance_url(instance_url)
        self.base_url = f"{self.instance_url}/api/now"
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Credentials
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        
        # OAuth token management
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0
        
        # Setup session with connection pooling and retry
        self._session = self._create_session()
        
        # Rate limiting state
        self._last_request_time: float = 0
        self._min_request_interval: float = 60.0 / calls_per_minute
    
    def _normalize_instance_url(self, url: str) -> str:
        """Normalize instance URL to standard format."""
        url = url.strip().rstrip("/")
        
        # Remove protocol if present
        if url.startswith("https://"):
            url = url[8:]
        elif url.startswith("http://"):
            url = url[7:]
        
        # Add .service-now.com if not present
        if ".service-now.com" not in url and ".servicenow.com" not in url:
            url = f"{url}.service-now.com"
        
        return f"https://{url}"
    
    def _create_session(self) -> requests.Session:
        """Create a session with connection pooling and retry."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _get_oauth_token(self) -> str:
        """Get OAuth 2.0 access token.
        
        Uses Resource Owner Password Credentials grant type.
        Per Zurich docs: Recommended for production integrations.
        """
        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        
        # Try refresh token first
        if self._refresh_token:
            try:
                return self._refresh_oauth_token()
            except ServiceNowAuthError:
                logger.info("Refresh token expired, requesting new token")
        
        if not self.client_id or not self.client_secret:
            raise ServiceNowAuthError(
                "OAuth credentials (client_id, client_secret) required"
            )
        
        token_url = f"{self.instance_url}/oauth_token.do"
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }
        
        try:
            response = requests.post(
                token_url, 
                data=data, 
                timeout=30,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            
            self._access_token = token_data["access_token"]
            self._refresh_token = token_data.get("refresh_token")
            
            # Set expiry with 60 second buffer
            expires_in = token_data.get("expires_in", 1800)
            self._token_expiry = time.time() + expires_in - 60
            
            logger.info("ServiceNow OAuth token acquired successfully")
            return self._access_token
            
        except requests.HTTPError as e:
            raise ServiceNowAuthError(f"OAuth token request failed: {e}") from e
    
    def _refresh_oauth_token(self) -> str:
        """Refresh OAuth token using refresh token."""
        if not self._refresh_token:
            raise ServiceNowAuthError("No refresh token available")
        
        token_url = f"{self.instance_url}/oauth_token.do"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        
        expires_in = token_data.get("expires_in", 1800)
        self._token_expiry = time.time() + expires_in - 60
        
        return self._access_token
    
    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        if self.client_id and self.client_secret:
            # OAuth 2.0
            headers["Authorization"] = f"Bearer {self._get_oauth_token()}"
        elif self.username and self.password:
            # Basic Authentication - handled by session auth
            pass
        else:
            raise ServiceNowAuthError("No authentication credentials configured")
        
        return headers
    
    def _get_auth(self) -> tuple[str, str] | None:
        """Get basic auth tuple if using basic auth."""
        if self.client_id and self.client_secret:
            return None  # Using OAuth
        elif self.username and self.password:
            return (self.username, self.password)
        return None
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses from ServiceNow API."""
        status_code = response.status_code
        
        # Try to extract error detail from response
        error_detail = {}
        try:
            error_data = response.json()
            if "error" in error_data:
                error_detail = error_data["error"]
        except Exception:
            error_detail = {"message": response.text[:500] if response.text else ""}
        
        if status_code == 401:
            # Clear OAuth token on auth failure
            self._access_token = None
            self._token_expiry = 0
            raise ServiceNowAuthError(
                f"Authentication failed: {error_detail.get('message', 'Invalid credentials')}",
                status_code,
                error_detail
            )
        elif status_code == 403:
            raise ServiceNowPermissionError(
                f"Insufficient permissions: {error_detail.get('message', 'Access denied')}",
                status_code,
                error_detail
            )
        elif status_code == 404:
            raise ServiceNowNotFoundError(
                f"Resource not found: {error_detail.get('message', 'Not found')}",
                status_code,
                error_detail
            )
        elif status_code == 409:
            raise ServiceNowConflictError(
                f"Conflict: {error_detail.get('message', 'Resource conflict')}",
                status_code,
                error_detail
            )
        elif status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            raise ServiceNowRateLimitError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                retry_after
            )
        elif status_code == 400:
            raise ServiceNowValidationError(
                f"Validation error: {error_detail.get('message', 'Bad request')}",
                status_code,
                error_detail
            )
        elif status_code >= 500:
            raise ServiceNowServerError(
                f"Server error: {error_detail.get('message', 'Internal server error')}",
                status_code,
                error_detail
            )
        else:
            raise ServiceNowAPIError(
                f"API error ({status_code}): {error_detail.get('message', 'Unknown error')}",
                status_code,
                error_detail
            )
    
    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        files: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to ServiceNow API.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            data: Form data (for file uploads)
            headers: Additional headers
            files: Files for multipart upload
            timeout: Request timeout override
            
        Returns:
            Response JSON data
        """
        self._apply_rate_limit()
        
        url = (
            urljoin(f"{self.instance_url}/", endpoint.lstrip("/"))
            if endpoint.startswith("api/")
            else urljoin(f"{self.base_url}/", endpoint.lstrip("/"))
        )
        
        # Merge headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)
        
        # For file uploads, don't set Content-Type (let requests handle it)
        if files:
            request_headers.pop("Content-Type", None)
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=request_headers,
                auth=self._get_auth(),
                files=files,
                timeout=timeout or self.timeout,
            )
            
            # Handle rate limiting with retry
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                return self.request(
                    method, endpoint, params, json_data, data, headers, files, timeout
                )
            
            # Handle error responses
            if not response.ok:
                self._handle_error_response(response)
            
            # Return JSON response or empty dict for 204 No Content
            if response.status_code == 204:
                return {}
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            raise ServiceNowAPIError(f"Request timeout: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ServiceNowAPIError(f"Connection error: {e}") from e
    
    def get(
        self, 
        endpoint: str, 
        params: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Make a GET request."""
        return self.request("GET", endpoint, params=params, **kwargs)
    
    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Make a POST request."""
        return self.request("POST", endpoint, json_data=json_data, **kwargs)
    
    def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Make a PUT request."""
        return self.request("PUT", endpoint, json_data=json_data, **kwargs)
    
    def patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Make a PATCH request."""
        return self.request("PATCH", endpoint, json_data=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make a DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def validate_connection(self) -> bool:
        """Validate that the connection is working."""
        try:
            # Try to access stats endpoint which requires minimal permissions
            self.get(f"{self.api_version}/stats/incident", params={"sysparm_count": "true"})
            return True
        except ServiceNowAPIError:
            # Fall back to table query
            try:
                self.get(f"{self.api_version}/table/incident", params={"sysparm_limit": "1"})
                return True
            except ServiceNowAPIError:
                return False
    
    def close(self) -> None:
        """Close the session."""
        self._session.close()
    
    def __enter__(self) -> "BaseServiceNowClient":
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
