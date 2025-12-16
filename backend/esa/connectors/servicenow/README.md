# ServiceNow Connector - Technical Documentation


## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Module Structure](#module-structure)
4. [Authentication](#authentication)
5. [Supported Content Types](#supported-content-types)
6. [Data Flow](#data-flow)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [Error Handling](#error-handling)
11. [Rate Limiting](#rate-limiting)
12. [Extending the Connector](#extending-the-connector)

---

## Overview

The ServiceNow Connector is a comprehensive integration module that connects ESA (Enterprise Search Application) to ServiceNow instances for document ingestion and indexing. It implements the **ServiceNow Table API v2** following the official Zurich API specification.

### Key Features

- ✅ **Multiple Authentication Methods**: OAuth 2.0 and Basic Authentication
- ✅ **Checkpoint-Based Pagination**: Reliable incremental sync with state persistence
- ✅ **Multi-Table Support**: ITSM, Knowledge, CMDB, CSM, HR, Service Catalog, Security Operations
- ✅ **Rate Limiting**: Built-in rate limiting with configurable thresholds
- ✅ **Error Recovery**: Graceful handling of inaccessible tables (ACL-based)
- ✅ **Custom Tables**: Support for extended configurations

### Current Testing Status

| Module | Status | Notes |
|--------|--------|-------|
| Incidents | ✅ Tested | Full integration verified |
| Problems | 🔲 Pending | Table mapping configured |
| Changes | 🔲 Pending | Table mapping configured |
| Knowledge | 🔲 Pending | Table mapping configured |
| CMDB | 🔲 Pending | Table mapping configured |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESA Indexing Engine                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ServiceNowConnector                              │
│  (connector.py)                                                  │
│                                                                  │
│  • load_credentials()      - Initialize client with creds       │
│  • load_from_checkpoint()  - Paginated document fetching        │
│  • validate_connector_settings() - Connection validation        │
│  • retrieve_all_slim_docs_perm_sync() - Permission sync         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              EnhancedServiceNowClient                            │
│  (enhanced_client.py)                                            │
│                                                                  │
│  • get_records_enhanced()  - Flexible record fetching           │
│  • get_task_by_number()    - Polymorphic task lookup            │
│  • get_ci_dependencies()   - Recursive CMDB traversal           │
│  • batch_resolve_references() - Batch reference resolution      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TableAPIClient                                 │
│  (table_api.py)                                                  │
│                                                                  │
│  • get_records()           - CRUD operations                    │
│  • get_records_paginated() - Auto-pagination iterator           │
│  • fetch_table_records()   - Legacy compat method               │
│  • build_query()           - Encoded query builder              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 BaseServiceNowClient                             │
│  (base_client.py)                                                │
│                                                                  │
│  • Session management with connection pooling                   │
│  • OAuth 2.0 token management (automatic refresh)               │
│  • Rate limiting with exponential backoff                       │
│  • Retry logic (3 attempts by default)                          │
│  • Comprehensive error handling                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              ServiceNow REST API (Zurich v2)                     │
│                                                                  │
│  Endpoint: /api/now/v2/table/{tableName}                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
esa/connectors/servicenow/
├── __init__.py              # Package initialization
├── connector.py             # Main connector class (ESA interface)
├── base_client.py           # Base HTTP client with auth/retry/rate-limiting
├── table_api.py             # Table API operations (CRUD)
├── enhanced_client.py       # Enhanced data model operations
├── client.py                # Legacy simple client (for reference)
├── aggregate_api.py         # Aggregate/Stats API
├── attachment_api.py        # Attachment handling
├── batch_api.py             # Batch operations
├── cmdb_api.py              # CMDB-specific operations
├── csm_api.py               # Customer Service Management
├── import_set_api.py        # Import Set operations
├── itsm_api.py              # ITSM-specific operations
├── knowledge_api.py         # Knowledge Management
├── service_catalog_api.py   # Service Catalog operations
├── asset_management_api.py  # Asset management
├── apireadme.md             # ServiceNow Data Model Guide
└── README.md                # This documentation
```

### Core Files Description

| File | Purpose |
|------|---------|
| `connector.py` | **Main entry point** - Implements ESA connector interfaces (`CheckpointedConnector`, `SlimConnectorWithPermSync`) |
| `base_client.py` | **Foundation layer** - HTTP session, authentication, rate limiting, error handling |
| `table_api.py` | **Table operations** - Full CRUD with pagination, query building, field configuration |
| `enhanced_client.py` | **Advanced features** - Dot-walking, polymorphic lookups, CMDB relationships |

---

## Authentication

The connector supports two authentication methods:

### Basic Authentication

```python
credentials = {
    "servicenow_instance_url": "https://dev314000.service-now.com",
    "servicenow_username": "admin",
    "servicenow_password": "your_password"
}
```

**Implementation**: Uses HTTP Basic Auth header via `requests` library.

### OAuth 2.0 (Recommended for Production)

```python
credentials = {
    "servicenow_instance_url": "https://your-instance.service-now.com",
    "servicenow_username": "service_account",
    "servicenow_password": "account_password",
    "servicenow_client_id": "your_client_id",
    "servicenow_client_secret": "your_client_secret"
}
```

**Implementation Details**:
- Grant Type: `password` (Resource Owner Password Credentials)
- Token Endpoint: `{instance_url}/oauth_token.do`
- Auto-refresh: Tokens refresh 60 seconds before expiry
- Token caching: Access tokens cached in memory

**Code Reference** (`base_client.py:187-239`):
```python
def _get_oauth_token(self) -> str:
    """Get OAuth 2.0 access token using Resource Owner Password Credentials grant."""
    if self._access_token and time.time() < self._token_expiry:
        return self._access_token
    
    # Try refresh token first, then request new token
    token_url = f"{self.instance_url}/oauth_token.do"
    data = {
        "grant_type": "password",
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "username": self.username,
        "password": self.password,
    }
    # ... token acquisition logic
```

---

## Supported Content Types

The connector maps content types to ServiceNow tables:

### ITSM (IT Service Management)

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `incidents` | `incident` | IT incidents |
| `problems` | `problem` | Problem records |
| `changes` | `change_request` | Change requests |
| `requests` | `sc_request`, `sc_req_item` | Service requests |
| `tasks` | `task`, `sc_task` | Generic tasks |
| `all_itsm` | Multiple | All ITSM tables |

### Knowledge Management

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `knowledge` | `kb_knowledge` | Knowledge articles |
| `all_knowledge` | `kb_knowledge` | All knowledge content |

### CMDB (Configuration Management Database)

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `cmdb_servers` | `cmdb_ci_server` | Server CIs |
| `cmdb_computers` | `cmdb_ci_computer` | Computer CIs |
| `cmdb_applications` | `cmdb_ci_appl` | Application CIs |
| `cmdb_services` | `cmdb_ci_service` | Service CIs |
| `cmdb_hardware` | `cmdb_ci_hardware` | Hardware CIs |
| `cmdb_all` | `cmdb_ci` | All CIs (base table) |

### Customer Service Management (CSM)

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `csm_cases` | `sn_customerservice_case` | Customer cases |
| `csm_accounts` | `customer_account` | Customer accounts |
| `csm_contacts` | `customer_contact` | Customer contacts |
| `csm_all` | Multiple | All CSM tables |

### HR Service Delivery

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `hr_cases` | `sn_hr_core_case` | HR cases |
| `hr_tasks` | `sn_hr_core_task` | HR tasks |
| `hr_all` | Multiple | All HR tables |

### Service Catalog

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `catalog_items` | `sc_cat_item` | Catalog items |
| `catalog_categories` | `sc_category` | Categories |
| `catalog_all` | Multiple | All catalog content |

### Security Operations

| Content Type | Table(s) | Description |
|--------------|----------|-------------|
| `security_incidents` | `sn_si_incident` | Security incidents |
| `security_vulnerabilities` | `sn_vul_vulnerable_item` | Vulnerabilities |
| `security_all` | Multiple | All security content |

---

## Data Flow

### Document Ingestion Flow

```
1. Connector Initialization
   ┌─────────────────────────────────────────────────────┐
   │ ServiceNowConnector(content_type="incidents")       │
   └─────────────────────────────────────────────────────┘
                          │
                          ▼
2. Credential Loading
   ┌─────────────────────────────────────────────────────┐
   │ connector.load_credentials({                        │
   │   "servicenow_instance_url": "...",                 │
   │   "servicenow_username": "...",                     │
   │   "servicenow_password": "..."                      │
   │ })                                                  │
   │ → Creates EnhancedServiceNowClient                  │
   └─────────────────────────────────────────────────────┘
                          │
                          ▼
3. Connection Validation
   ┌─────────────────────────────────────────────────────┐
   │ connector.validate_connector_settings()             │
   │ → Fetches 1 record from incident table              │
   │ → Validates auth and table access                   │
   └─────────────────────────────────────────────────────┘
                          │
                          ▼
4. Document Fetching (Checkpoint-based)
   ┌─────────────────────────────────────────────────────┐
   │ connector.load_from_checkpoint(start, end, chkpt)   │
   │                                                     │
   │ For each table in content_type:                     │
   │   → client.fetch_table_records(table, offset, limit)│
   │   → Convert records to ESA Documents                │
   │   → Yield documents                                 │
   │   → Update checkpoint                               │
   └─────────────────────────────────────────────────────┘
                          │
                          ▼
5. Document Conversion
   ┌─────────────────────────────────────────────────────┐
   │ _record_to_document(record, table_name)             │
   │                                                     │
   │ Extracts:                                           │
   │   - sys_id → Document ID                            │
   │   - short_description → Title                       │
   │   - description/text → Content (HTML parsed)        │
   │   - sys_updated_on → Update timestamp               │
   │   - state, priority, etc → Metadata                 │
   │   - URL → nav_to.do link                           │
   └─────────────────────────────────────────────────────┘
```

### Checkpoint Structure

```python
class ServiceNowConnectorCheckpoint(ConnectorCheckpoint):
    """Tracks pagination state across multiple tables."""
    
    table_offsets: dict[str, int]    # Offset per table
    current_table_index: int          # Current table in list
    has_more: bool                    # More data available
```

**Example Checkpoint State**:
```json
{
  "table_offsets": {
    "incident": 200,
    "problem": 0
  },
  "current_table_index": 0,
  "has_more": true
}
```

---

## API Reference

### ServiceNowConnector (Main Class)

```python
class ServiceNowConnector(
    SlimConnectorWithPermSync,
    CheckpointedConnector[ServiceNowConnectorCheckpoint],
):
    """Main connector class implementing ESA interfaces."""
    
    def __init__(
        self,
        content_type: str = "all_itsm",
        custom_tables: str | None = None,
        calls_per_minute: int = 600,
    ) -> None:
        """Initialize connector.
        
        Args:
            content_type: Type of content to index (see CONTENT_TYPE_TABLES)
            custom_tables: Comma-separated list of additional tables
            calls_per_minute: API rate limit
        """
    
    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Load ServiceNow credentials and initialize client."""
    
    def validate_connector_settings(self) -> None:
        """Validate credentials and connectivity."""
    
    def load_from_checkpoint(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: ServiceNowConnectorCheckpoint,
    ) -> CheckpointOutput[ServiceNowConnectorCheckpoint]:
        """Load documents with checkpoint-based pagination."""
    
    def retrieve_all_slim_docs_perm_sync(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: IndexingHeartbeatInterface | None = None,
    ) -> GenerateSlimDocumentOutput:
        """Retrieve slim documents for permission sync."""
    
    def build_dummy_checkpoint(self) -> ServiceNowConnectorCheckpoint:
        """Build initial empty checkpoint."""
```

### EnhancedServiceNowClient

```python
class EnhancedServiceNowClient(TableAPIClient):
    """Enhanced client with data model relationship support."""
    
    def get_records_enhanced(
        self,
        table: str,
        query: str | None = None,
        fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Get records with flexible configuration."""
    
    def get_task_by_number(self, task_number: str) -> dict[str, Any] | None:
        """Get any task by number, auto-determining table."""
    
    def get_ci_dependencies(
        self,
        ci_sys_id: str,
        depth: int = 1,
        direction: str = "parent",
    ) -> list[dict[str, Any]]:
        """Get CI dependencies recursively."""
    
    def batch_resolve_references(
        self,
        records: list[dict[str, Any]],
        reference_fields: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Batch resolve reference fields."""
```

### TableAPIClient

```python
class TableAPIClient(BaseServiceNowClient):
    """Table API client for CRUD operations."""
    
    def get_records(
        self,
        table_name: str,
        offset: int = 0,
        limit: int = 100,
        query: str | None = None,
        fields: str | None = None,
        order_by: str | None = None,
        display_value: str = "all",
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Fetch records from a table."""
    
    def get_record(
        self,
        table_name: str,
        sys_id: str,
    ) -> dict[str, Any]:
        """Get a single record by sys_id."""
    
    def create_record(
        self,
        table_name: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new record."""
    
    def update_record(
        self,
        table_name: str,
        sys_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a record (PATCH)."""
    
    def delete_record(
        self,
        table_name: str,
        sys_id: str,
    ) -> bool:
        """Delete a record."""
    
    def fetch_table_records(
        self,
        table_name: str,
        offset: int = 0,
        limit: int = 100,
        updated_after: float | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch records with has_more indicator (Legacy compat)."""
```

---

## Configuration

### Environment Variables

The connector can be configured via environment variables for testing:

```bash
# Required
SERVICENOW_INSTANCE=https://your-instance.service-now.com
SERVICENOW_USERNAME=service_account
SERVICENOW_PASSWORD=password

# Optional (OAuth)
SERVICENOW_CLIENT_ID=your_client_id
SERVICENOW_CLIENT_SECRET=your_client_secret
```

### Connector Configuration in ESA

When configuring via the ESA UI:

```yaml
Connector Type: servicenow
Content Type: incidents  # or "all_itsm", "knowledge", etc.
Custom Tables: ""        # Optional comma-separated list

Credentials:
  servicenow_instance_url: "https://your-instance.service-now.com"
  servicenow_username: "service_account"
  servicenow_password: "password"
  # Optional OAuth
  servicenow_client_id: "client_id"
  servicenow_client_secret: "client_secret"
```

### Table Field Configuration

Each table has preconfigured field mappings in `table_api.py`:

```python
TABLE_CONFIGS = {
    "incident": {
        "fields": "sys_id,number,short_description,description,state,priority,urgency,impact,...",
        "display_field": "number",
        "order_by": "sys_updated_on",
    },
    # ... 50+ table configurations
}
```

---

## Testing

### Test Files Location

```
backend/tests/servicenow/
├── test_servicenow_clients.py      # Unit tests for clients
├── verify_connector_orchestration.py  # Integration test
└── debug_connector_logic.py        # Debug/development script

backend/scripts/
├── test_servicenow_live.py         # Live API testing
└── test_servicenow_catalog.py      # Service Catalog testing
```

### Running Unit Tests

```bash
cd backend
python -m pytest tests/servicenow/test_servicenow_clients.py -v
```

### Running Integration Tests

```bash
cd backend
python tests/servicenow/verify_connector_orchestration.py
```

**Expected Output**:
```
--- Starting ServiceNow Connector Orchestration Verification ---
✅ Credentials loaded.
✅ Connection validated (validate_connector_settings).
--- Fetching Documents (Incidents) ---
📄 Found Document: servicenow_incident_abc123...
   - Title: Incident INC0001234: Network issue
   - Link: https://dev314000.service-now.com/nav_to.do?uri=incident.do...
   - Metadata: {'table': 'incident', 'state': 'New', 'priority': '3'}
... stopping after 3 docs ...
✅ Successfully fetched 3 documents.
🎉 Connector Orchestration Verified!
```

### Running Live API Tests

```bash
cd backend
python scripts/test_servicenow_live.py
```

### Test Results Summary (Current)

| Test | Result | Notes |
|------|--------|-------|
| EnhancedServiceNowClient connection | ✅ Pass | Basic auth verified |
| Incident table fetch | ✅ Pass | Records retrieved successfully |
| Knowledge articles fetch | ✅ Pass | KB articles accessible |
| Full connector pipeline | ✅ Pass | Documents generated correctly |
| Checkpoint pagination | ✅ Pass | State maintained across calls |

---

## Error Handling

The connector implements comprehensive error handling:

### Exception Hierarchy

```python
ServiceNowAPIError                # Base exception
├── ServiceNowAuthError           # 401 - Authentication failed
├── ServiceNowPermissionError     # 403 - Insufficient permissions
├── ServiceNowNotFoundError       # 404 - Resource not found
├── ServiceNowRateLimitError      # 429 - Rate limit exceeded
├── ServiceNowConflictError       # 409 - Concurrent update conflict
├── ServiceNowValidationError     # 400 - Bad request
└── ServiceNowServerError         # 5xx - Server errors
```

### Connector-Specific Exceptions

```python
ServiceNowCredentialsError        # Credentials not configured
CredentialExpiredError           # OAuth token expired (ESA interface)
InsufficientPermissionsError     # ACL denied (ESA interface)
ConnectorValidationError         # Connection failed (ESA interface)
```

### Error Recovery Behavior

| Error | Behavior |
|-------|----------|
| 401 Auth Failed | Clear OAuth token, raise `CredentialExpiredError` |
| 403 Permission Denied | Skip table, log warning, continue with next table |
| 404 Not Found | Skip table (plugin not installed), continue |
| 429 Rate Limited | Wait `Retry-After` seconds, retry |
| 5xx Server Error | Retry with exponential backoff (3 attempts) |

### Code Example (Error Handling in Connector)

```python
def load_from_checkpoint(self, start, end, checkpoint):
    while checkpoint.current_table_index < len(tables):
        table_name = tables[checkpoint.current_table_index]
        
        try:
            records, has_more = self.client.fetch_table_records(...)
        except ServiceNowPermissionError as e:
            # Skip tables user doesn't have ACL access to
            logger.warning(f"Skipping {table_name} - insufficient permissions")
            checkpoint.current_table_index += 1
            continue
        except ServiceNowNotFoundError as e:
            # Skip tables that don't exist (plugin-dependent)
            logger.warning(f"Skipping {table_name} - table not found")
            checkpoint.current_table_index += 1
            continue
        
        # Process records...
```

---

## Rate Limiting

### Default Configuration

```python
DEFAULT_RATE_LIMIT = 30  # requests per minute (conservative)
```

### ServiceNow Rate Limits (per Zurich docs)

| Instance Type | Limit |
|---------------|-------|
| Personal Developer | 1,800 requests/hour/user |
| Enterprise | 7,200 requests/hour/user |

### Rate Limiting Implementation

**Location**: `base_client.py:292-297`

```python
def _apply_rate_limit(self) -> None:
    """Apply rate limiting between requests."""
    elapsed = time.time() - self._last_request_time
    if elapsed < self._min_request_interval:
        time.sleep(self._min_request_interval - elapsed)
    self._last_request_time = time.time()
```

### 429 Response Handling

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "60"))
    logger.warning(f"Rate limited, waiting {retry_after}s")
    time.sleep(retry_after)
    return self.request(...)  # Retry
```

---

## Extending the Connector

### Adding New Content Types

1. **Update `CONTENT_TYPE_TABLES` in `connector.py`**:

```python
CONTENT_TYPE_TABLES = {
    # Existing types...
    
    # Add new type
    "my_custom_type": ["custom_table_1", "custom_table_2"],
}
```

2. **Add table configuration in `table_api.py`**:

```python
TABLE_CONFIGS = {
    # Existing configs...
    
    "custom_table_1": {
        "fields": "sys_id,name,description,state,sys_updated_on",
        "display_field": "name",
        "order_by": "sys_updated_on",
    },
}
```

### Adding New API Clients

Create a new module extending `BaseServiceNowClient`:

```python
# new_api.py
from esa.connectors.servicenow.base_client import BaseServiceNowClient

class NewAPIClient(BaseServiceNowClient):
    """Client for ServiceNow New API."""
    
    def custom_operation(self, **kwargs):
        """Implement custom API logic."""
        endpoint = f"{self.api_version}/new_api/action"
        return self.get(endpoint, params=kwargs)
```

### Custom Document Conversion

Override `_record_to_document` in a subclass:

```python
class CustomServiceNowConnector(ServiceNowConnector):
    def _record_to_document(self, record, table_name):
        # Custom conversion logic
        doc = super()._record_to_document(record, table_name)
        
        # Add custom metadata
        doc.metadata["custom_field"] = record.get("custom_field")
        
        return doc
```

---

## Appendix

### ServiceNow Table Reference

| Table | Description | Common Fields |
|-------|-------------|---------------|
| `incident` | IT Incidents | number, short_description, state, priority |
| `problem` | Problem records | number, short_description, known_error |
| `change_request` | Change requests | number, type, risk, state |
| `kb_knowledge` | Knowledge articles | number, text, workflow_state |
| `cmdb_ci` | Configuration Items | name, operational_status |
| `sys_user` | Users | user_name, name, email |
| `sys_user_group` | Groups | name, manager |

### Document ID Format

```
servicenow_{table_name}_{sys_id}
```

Example: `servicenow_incident_abc123def456...`

### URL Format

```
{instance_url}/nav_to.do?uri={table_name}.do?sys_id={sys_id}
```

Example: `https://dev314000.service-now.com/nav_to.do?uri=incident.do?sys_id=abc123`

---

## Support & Troubleshooting

### Common Issues

1. **Authentication Fails (401)**
   - Verify username/password
   - Check if OAuth credentials are correct
   - Ensure user account is not locked

2. **Permission Denied (403)**
   - Verify service account has table read access
   - Check ServiceNow ACL rules
   - Ensure correct roles assigned

3. **No Documents Returned**
   - Check date range (start/end timestamps)
   - Verify table has data
   - Check query filters

4. **Rate Limit Exceeded (429)**
   - Reduce `calls_per_minute` configuration
   - Check other integrations using same account

### Debug Logging

Enable debug logging:

```python
import logging
logging.getLogger("esa.connectors.servicenow").setLevel(logging.DEBUG)
```
