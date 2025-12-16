# ServiceNow Connector - Architecture Overview

> Use this document to create detailed architecture diagrams

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ESA PLATFORM                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Indexing Engine                                  │   │
│  │                                                                      │   │
│  │  • Document Processing Pipeline                                     │   │
│  │  • Vector Store (Embeddings)                                        │   │
│  │  • Search/Query Engine                                              │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                    Calls connector.load_from_checkpoint()                  │
│                                 │                                           │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │              ServiceNowConnector (connector.py)                      │   │
│  │                                                                      │   │
│  │  Implements: CheckpointedConnector, SlimConnectorWithPermSync       │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ HTTPS/REST
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICENOW INSTANCE                                  │
│                     (https://instance.service-now.com)                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    REST API (Zurich v2)                             │    │
│  │                 /api/now/v2/table/{tableName}                       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   ITSM       │  │  Knowledge   │  │    CMDB      │  │    CSM       │   │
│  │  incident    │  │ kb_knowledge │  │   cmdb_ci    │  │   csm_case   │   │
│  │  problem     │  │ kb_category  │  │ cmdb_ci_*    │  │  customer_*  │   │
│  │  change_req  │  └──────────────┘  │ cmdb_rel_ci  │  └──────────────┘   │
│  │  sc_request  │                    └──────────────┘                      │
│  └──────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Connector Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICENOW CONNECTOR PACKAGE                         │
│                      esa/connectors/servicenow/                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │  LAYER 1: ESA INTERFACE                                                ││
│  │  ┌──────────────────────────────────────────────────────────────────┐ ││
│  │  │  ServiceNowConnector (connector.py)                              │ ││
│  │  │                                                                  │ ││
│  │  │  Methods:                                                        │ ││
│  │  │  • load_credentials(dict) → Initialize client                   │ ││
│  │  │  • validate_connector_settings() → Test connection              │ ││
│  │  │  • load_from_checkpoint(start, end, checkpoint) → Fetch docs    │ ││
│  │  │  • retrieve_all_slim_docs_perm_sync() → Permission sync         │ ││
│  │  │  • build_dummy_checkpoint() → Initial state                     │ ││
│  │  │                                                                  │ ││
│  │  │  Inputs: Credentials, Content Type, Custom Tables               │ ││
│  │  │  Outputs: ESA Document objects, Checkpoints                     │ ││
│  │  └──────────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    │ uses                                   │
│                                    ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │  LAYER 2: ENHANCED DATA MODEL                                          ││
│  │  ┌──────────────────────────────────────────────────────────────────┐ ││
│  │  │  EnhancedServiceNowClient (enhanced_client.py)                   │ ││
│  │  │                                                                  │ ││
│  │  │  Methods:                                                        │ ││
│  │  │  • get_records_enhanced() → Flexible queries                    │ ││
│  │  │  • get_task_by_number() → Polymorphic task lookup (INC/CHG/PRB) │ ││
│  │  │  • get_ci_dependencies() → Recursive CMDB traversal             │ ││
│  │  │  • batch_resolve_references() → Bulk reference resolution       │ ││
│  │  │  • build_dot_walk_query() → Related field queries               │ ││
│  │  │  • get_m2m_relationships() → Many-to-many lookups               │ ││
│  │  └──────────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    │ extends                                │
│                                    ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │  LAYER 3: TABLE API                                                    ││
│  │  ┌──────────────────────────────────────────────────────────────────┐ ││
│  │  │  TableAPIClient (table_api.py)                                   │ ││
│  │  │                                                                  │ ││
│  │  │  Methods:                                                        │ ││
│  │  │  • get_records() → Paginated table queries                      │ ││
│  │  │  • get_record() → Single record by sys_id                       │ ││
│  │  │  • create_record() → POST new record                            │ ││
│  │  │  • update_record() → PATCH existing record                      │ ││
│  │  │  • delete_record() → DELETE record                              │ ││
│  │  │  • fetch_table_records() → Legacy compat wrapper                │ ││
│  │  │  • build_query() → Encoded query builder                        │ ││
│  │  │  • build_record_url() → Generate UI links                       │ ││
│  │  │                                                                  │ ││
│  │  │  Config: TABLE_CONFIGS (50+ table field mappings)               │ ││
│  │  └──────────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    │ extends                                │
│                                    ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │  LAYER 4: BASE HTTP CLIENT                                             ││
│  │  ┌──────────────────────────────────────────────────────────────────┐ ││
│  │  │  BaseServiceNowClient (base_client.py)                           │ ││
│  │  │                                                                  │ ││
│  │  │  Core Features:                                                  │ ││
│  │  │  • Session Management (connection pooling)                      │ ││
│  │  │  • Authentication (Basic Auth / OAuth 2.0)                      │ ││
│  │  │  • Rate Limiting (configurable req/min)                         │ ││
│  │  │  • Retry Logic (exponential backoff, 3 attempts)                │ ││
│  │  │  • Error Handling (401/403/404/429/5xx)                         │ ││
│  │  │                                                                  │ ││
│  │  │  Methods:                                                        │ ││
│  │  │  • request(method, endpoint, params, json_data)                 │ ││
│  │  │  • get(), post(), put(), patch(), delete()                      │ ││
│  │  │  • _get_oauth_token() → Token management                        │ ││
│  │  │  • _apply_rate_limit() → Throttling                             │ ││
│  │  │  • _handle_error_response() → Exception mapping                 │ ││
│  │  └──────────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS (requests library)
                                    ▼
                    ┌───────────────────────────────┐
                    │    ServiceNow REST API        │
                    │   /api/now/v2/table/{table}   │
                    └───────────────────────────────┘
```

---

## Data Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   ESA        │     │  Connector   │     │   Client     │     │ ServiceNow   │
│  Indexer     │     │   Layer      │     │   Layer      │     │    API       │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │                    │
       │  1. Initialize     │                    │                    │
       │─────────────────-->│                    │                    │
       │                    │                    │                    │
       │  2. load_credentials                    │                    │
       │─────────────────-->│                    │                    │
       │                    │  3. Create client  │                    │
       │                    │─────────────────-->│                    │
       │                    │                    │                    │
       │  4. validate_connector_settings         │                    │
       │─────────────────-->│                    │                    │
       │                    │  5. fetch_table_records (limit=1)       │
       │                    │─────────────────-->│                    │
       │                    │                    │  6. GET /table/incident
       │                    │                    │─────────────────-->│
       │                    │                    │  7. JSON response  │
       │                    │                    │<───────────────────│
       │                    │  8. records[]      │                    │
       │                    │<───────────────────│                    │
       │  9. Validated OK   │                    │                    │
       │<───────────────────│                    │                    │
       │                    │                    │                    │
       │  10. load_from_checkpoint(start, end, checkpoint)           │
       │─────────────────-->│                    │                    │
       │                    │                    │                    │
       │                    │ ┌────────────────────────────────────┐ │
       │                    │ │  FOR EACH TABLE IN CONTENT_TYPE   │ │
       │                    │ └──────────────┬─────────────────────┘ │
       │                    │                │                       │
       │                    │  11. fetch_table_records(offset, limit)│
       │                    │─────────────────-->│                   │
       │                    │                    │  12. GET /table/{t}
       │                    │                    │─────────────────-->│
       │                    │                    │  13. records[]    │
       │                    │                    │<───────────────────│
       │                    │  14. records, has_more                 │
       │                    │<───────────────────│                   │
       │                    │                    │                    │
       │                    │  15. _record_to_document()             │
       │                    │      (for each record)                 │
       │                    │                    │                    │
       │  16. yield Document│                    │                    │
       │<───────────────────│                    │                    │
       │                    │                    │                    │
       │  17. Update checkpoint, continue or finish                  │
       │                    │                    │                    │
```

---

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION METHODS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────┐  ┌────────────────────────────────┐    │
│  │      BASIC AUTHENTICATION      │  │      OAUTH 2.0 (Recommended)   │    │
│  ├────────────────────────────────┤  ├────────────────────────────────┤    │
│  │                                │  │                                │    │
│  │  Credentials:                  │  │  Credentials:                  │    │
│  │  • servicenow_instance_url     │  │  • servicenow_instance_url     │    │
│  │  • servicenow_username         │  │  • servicenow_username         │    │
│  │  • servicenow_password         │  │  • servicenow_password         │    │
│  │                                │  │  • servicenow_client_id        │    │
│  │                                │  │  • servicenow_client_secret    │    │
│  ├────────────────────────────────┤  ├────────────────────────────────┤    │
│  │                                │  │                                │    │
│  │  Flow:                         │  │  Flow:                         │    │
│  │                                │  │                                │    │
│  │   Client                API    │  │   Client              API      │    │
│  │     │                    │     │  │     │                  │       │    │
│  │     │ Authorization:     │     │  │     │ POST /oauth_token.do     │    │
│  │     │ Basic base64(u:p)  │     │  │     │ grant_type=password      │    │
│  │     │─────────────────-->│     │  │     │ client_id, secret        │    │
│  │     │                    │     │  │     │ username, password       │    │
│  │     │   200 OK + data    │     │  │     │───────────────────>│     │    │
│  │     │<───────────────────│     │  │     │                    │     │    │
│  │                                │  │     │ {access_token,     │     │    │
│  │                                │  │     │  refresh_token,    │     │    │
│  │                                │  │     │  expires_in}       │     │    │
│  │                                │  │     │<───────────────────│     │    │
│  │                                │  │     │                    │     │    │
│  │                                │  │     │ Authorization:     │     │    │
│  │                                │  │     │ Bearer {token}     │     │    │
│  │                                │  │     │───────────────────>│     │    │
│  │                                │  │                                │    │
│  └────────────────────────────────┘  └────────────────────────────────┘    │
│                                                                              │
│  Token Lifecycle:                                                           │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────────┐  │
│  │ Request │───>│ Check Cache  │───>│ Token Valid?│───>│ Use Token     │  │
│  │ Token   │    │              │    │             │    │               │  │
│  └─────────┘    └──────────────┘    └──────┬──────┘    └───────────────┘  │
│                                            │ No                            │
│                                            ▼                               │
│                                   ┌─────────────────┐                      │
│                                   │ Refresh Token?  │                      │
│                                   └────────┬────────┘                      │
│                                     Yes │    │ No                          │
│                                         ▼    ▼                             │
│                          ┌──────────────────────────────┐                  │
│                          │ POST /oauth_token.do         │                  │
│                          │ (refresh or password grant)  │                  │
│                          └──────────────────────────────┘                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Content Type to Table Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTENT TYPE → TABLE MAPPING                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │  Content Type   │                                                        │
│  │  (User Input)   │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                      CONTENT_TYPE_TABLES                               ││
│  ├────────────────────────────────────────────────────────────────────────┤│
│  │                                                                        ││
│  │  "incidents"        ──────────────────────────>  ["incident"]          ││
│  │  "problems"         ──────────────────────────>  ["problem"]           ││
│  │  "changes"          ──────────────────────────>  ["change_request"]    ││
│  │  "requests"         ──────────────────────────>  ["sc_request",        ││
│  │                                                   "sc_req_item"]       ││
│  │  "tasks"            ──────────────────────────>  ["task", "sc_task"]   ││
│  │                                                                        ││
│  │  "knowledge"        ──────────────────────────>  ["kb_knowledge"]      ││
│  │                                                                        ││
│  │  "cmdb_servers"     ──────────────────────────>  ["cmdb_ci_server"]    ││
│  │  "cmdb_computers"   ──────────────────────────>  ["cmdb_ci_computer"]  ││
│  │  "cmdb_applications"──────────────────────────>  ["cmdb_ci_appl"]      ││
│  │  "cmdb_services"    ──────────────────────────>  ["cmdb_ci_service"]   ││
│  │  "cmdb_all"         ──────────────────────────>  ["cmdb_ci"]           ││
│  │                                                                        ││
│  │  "csm_cases"        ──────────────────────────>  ["sn_customerservice_case"]
│  │  "csm_accounts"     ──────────────────────────>  ["customer_account"]  ││
│  │  "csm_contacts"     ──────────────────────────>  ["customer_contact"]  ││
│  │                                                                        ││
│  │  "hr_cases"         ──────────────────────────>  ["sn_hr_core_case"]   ││
│  │  "hr_tasks"         ──────────────────────────>  ["sn_hr_core_task"]   ││
│  │                                                                        ││
│  │  "catalog_items"    ──────────────────────────>  ["sc_cat_item"]       ││
│  │  "catalog_categories"─────────────────────────>  ["sc_category"]       ││
│  │                                                                        ││
│  │  "security_incidents"─────────────────────────>  ["sn_si_incident"]    ││
│  │  "security_vulnerabilities"───────────────────>  ["sn_vul_vulnerable_item"]
│  │                                                                        ││
│  │  "all_itsm"         ──────────────────────────>  ["incident",          ││
│  │                                                   "problem",           ││
│  │                                                   "change_request",    ││
│  │                                                   "task"]              ││
│  │                                                                        ││
│  │  "all"              ──────────────────────────>  [All major tables]    ││
│  │                                                                        ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ERROR HANDLING FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   API Response                                                              │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐                                                            │
│  │ Status Code │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│    ┌────┴────┬────────┬────────┬────────┬────────┬────────┐                │
│    │         │        │        │        │        │        │                │
│    ▼         ▼        ▼        ▼        ▼        ▼        ▼                │
│ ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐            │
│ │ 200 │  │ 401 │  │ 403 │  │ 404 │  │ 429 │  │ 400 │  │ 5xx │            │
│ │ OK  │  │     │  │     │  │     │  │     │  │     │  │     │            │
│ └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘            │
│    │        │        │        │        │        │        │                │
│    ▼        ▼        ▼        ▼        ▼        ▼        ▼                │
│ ┌──────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│ │Return│ │Clear     │ │Skip      │ │Skip      │ │Wait      │ │Retry     ││
│ │Data  │ │OAuth     │ │Table     │ │Table     │ │Retry-    │ │with      ││
│ │      │ │Token     │ │Continue  │ │Continue  │ │After     │ │Backoff   ││
│ │      │ │Raise     │ │Next      │ │Next      │ │Header    │ │(3x)      ││
│ │      │ │AuthError │ │          │ │          │ │Retry     │ │          ││
│ └──────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                                                                              │
│  Exception Hierarchy:                                                       │
│                                                                              │
│  ServiceNowAPIError (Base)                                                  │
│     │                                                                        │
│     ├── ServiceNowAuthError ────────────> CredentialExpiredError (ESA)     │
│     ├── ServiceNowPermissionError ──────> InsufficientPermissionsError     │
│     ├── ServiceNowNotFoundError ────────> Skip table, log warning          │
│     ├── ServiceNowRateLimitError ───────> Sleep and retry                  │
│     ├── ServiceNowConflictError ────────> Retry on concurrent updates      │
│     ├── ServiceNowValidationError ──────> Log and skip record              │
│     └── ServiceNowServerError ──────────> Retry with backoff               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Document Conversion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SERVICENOW RECORD → ESA DOCUMENT                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ServiceNow Record (JSON)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ {                                                                   │   │
│  │   "sys_id": "abc123def456...",                                      │   │
│  │   "number": "INC0001234",                                           │   │
│  │   "short_description": "Network connectivity issue",                │   │
│  │   "description": "<p>Detailed HTML description...</p>",             │   │
│  │   "state": {"value": "1", "display_value": "New"},                  │   │
│  │   "priority": {"value": "3", "display_value": "Moderate"},         │   │
│  │   "sys_updated_on": "2024-12-15 10:30:00"                          │   │
│  │ }                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                     _record_to_document()                                   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Transformation Steps:                                               │   │
│  │                                                                     │   │
│  │ 1. Extract sys_id ────────────────> Document ID (prefixed)         │   │
│  │    "abc123" → "servicenow_incident_abc123"                         │   │
│  │                                                                     │   │
│  │ 2. Get display field ─────────────> Semantic Identifier            │   │
│  │    number="INC0001234" + short_description                         │   │
│  │    → "Incident INC0001234: Network connectivity issue"             │   │
│  │                                                                     │   │
│  │ 3. Parse HTML content ────────────> Plain text                     │   │
│  │    parse_html_page_basic(description)                              │   │
│  │                                                                     │   │
│  │ 4. Build document text ───────────> TextSection                    │   │
│  │    "Incident: INC0001234\n\nNetwork connectivity...\n\nDetails..." │   │
│  │                                                                     │   │
│  │ 5. Build URL ─────────────────────> link                           │   │
│  │    "{instance}/nav_to.do?uri=incident.do?sys_id=abc123"           │   │
│  │                                                                     │   │
│  │ 6. Parse timestamp ───────────────> doc_updated_at                 │   │
│  │    time_str_to_utc("2024-12-15 10:30:00")                          │   │
│  │                                                                     │   │
│  │ 7. Extract metadata ──────────────> metadata dict                  │   │
│  │    {table, state, priority, urgency, impact, category...}         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ESA Document                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Document(                                                           │   │
│  │   id="servicenow_incident_abc123def456",                           │   │
│  │   source=DocumentSource.SERVICENOW,                                │   │
│  │   semantic_identifier="Incident INC0001234: Network connectivity", │   │
│  │   sections=[TextSection(link="...", text="...")],                  │   │
│  │   doc_updated_at=datetime(2024, 12, 15, 10, 30, 0),               │   │
│  │   metadata={"table": "incident", "state": "New", "priority": "3"}  │   │
│  │ )                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Rate Limiting Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RATE LIMITING ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Configuration                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  calls_per_minute = 600  (default)                                  │   │
│  │  _min_request_interval = 60.0 / calls_per_minute = 0.1 seconds     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Request Flow                                                               │
│  ┌─────────────┐                                                            │
│  │   Request   │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  _apply_rate_limit()                                                │   │
│  │                                                                     │   │
│  │  elapsed = current_time - last_request_time                        │   │
│  │                                                                     │   │
│  │  if elapsed < min_interval:                                        │   │
│  │      sleep(min_interval - elapsed)                                 │   │
│  │                                                                     │   │
│  │  last_request_time = current_time                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │  HTTP       │                                                            │
│  │  Request    │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Response Status = 429?                                             │   │
│  │                                                                     │   │
│  │  YES:                                                               │   │
│  │    retry_after = headers.get("Retry-After", 60)                    │   │
│  │    sleep(retry_after)                                              │   │
│  │    retry_request()                                                 │   │
│  │                                                                     │   │
│  │  NO:                                                                │   │
│  │    continue_processing()                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ServiceNow Limits (Zurich)                                                │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Instance Type          │ Limit                                    │    │
│  │  ──────────────────────────────────────────────────────────────   │    │
│  │  Personal Developer     │ 1,800 requests/hour/user                │    │
│  │  Enterprise             │ 7,200 requests/hour/user                │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Class Inheritance Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLASS INHERITANCE HIERARCHY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ESA Interfaces                  ServiceNow Client Classes                  │
│  ─────────────                   ────────────────────────                   │
│                                                                              │
│  ┌────────────────────┐          ┌────────────────────────┐                │
│  │CheckpointedConnector│          │  BaseServiceNowClient  │                │
│  │[ServiceNowConnector │          │  (ABC)                 │                │
│  │ Checkpoint]         │          │                        │                │
│  └─────────┬───────────┘          │  • Session management  │                │
│            │                      │  • Authentication      │                │
│  ┌─────────┴───────────┐          │  • Rate limiting       │                │
│  │SlimConnectorWith    │          │  • Error handling      │                │
│  │PermSync             │          │  • HTTP methods        │                │
│  └─────────┬───────────┘          └───────────┬────────────┘                │
│            │                                  │                              │
│            │                                  │ extends                      │
│            │                                  ▼                              │
│            │                      ┌────────────────────────┐                │
│            │                      │    TableAPIClient      │                │
│            │                      │                        │                │
│            │                      │  • CRUD operations     │                │
│            │                      │  • Query building      │                │
│            │                      │  • Pagination          │                │
│            │                      │  • TABLE_CONFIGS       │                │
│            │                      └───────────┬────────────┘                │
│            │                                  │                              │
│            │                                  │ extends                      │
│            │                                  ▼                              │
│            │                      ┌────────────────────────┐                │
│            │                      │EnhancedServiceNowClient│                │
│            │                      │                        │                │
│            │                      │  • Polymorphic lookup  │                │
│            │                      │  • Dot-walking         │                │
│            │                      │  • CMDB relationships  │                │
│            │                      │  • Batch resolution    │                │
│            │                      └───────────┬────────────┘                │
│            │                                  │                              │
│            │     ┌────────────────────────────┘                             │
│            │     │ uses                                                      │
│            ▼     ▼                                                           │
│  ┌──────────────────────────────┐                                           │
│  │    ServiceNowConnector       │                                           │
│  │                              │                                           │
│  │  • load_credentials()        │                                           │
│  │  • validate_connector()      │                                           │
│  │  • load_from_checkpoint()    │                                           │
│  │  • _record_to_document()     │                                           │
│  │                              │                                           │
│  │  Contains: EnhancedClient    │                                           │
│  └──────────────────────────────┘                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FILE DEPENDENCIES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  connector.py                                                               │
│     │                                                                        │
│     ├── imports ──> enhanced_client.py                                      │
│     ├── imports ──> client.py (exceptions only)                             │
│     ├── imports ──> ESA interfaces (CheckpointedConnector, etc.)           │
│     └── imports ──> ESA models (Document, TextSection, etc.)               │
│                                                                              │
│  enhanced_client.py                                                         │
│     │                                                                        │
│     └── extends ──> table_api.py (TableAPIClient)                          │
│                                                                              │
│  table_api.py                                                               │
│     │                                                                        │
│     └── extends ──> base_client.py (BaseServiceNowClient)                  │
│                                                                              │
│  base_client.py                                                             │
│     │                                                                        │
│     ├── imports ──> requests (HTTP library)                                 │
│     └── imports ──> urllib3 (Retry)                                         │
│                                                                              │
│  client.py (Legacy)                                                         │
│     │                                                                        │
│     ├── imports ──> requests                                                │
│     └── exports ──> Exception classes (used by connector.py)               │
│                                                                              │
│                                                                              │
│  Diagram:                                                                   │
│                                                                              │
│           ESA Platform                                                      │
│               │                                                              │
│               ▼                                                              │
│       ┌───────────────┐                                                     │
│       │ connector.py  │                                                     │
│       └───────┬───────┘                                                     │
│               │                                                              │
│               ▼                                                              │
│  ┌────────────────────────┐                                                 │
│  │ enhanced_client.py     │                                                 │
│  └────────────┬───────────┘                                                 │
│               │                                                              │
│               ▼                                                              │
│       ┌───────────────┐                                                     │
│       │ table_api.py  │                                                     │
│       └───────┬───────┘                                                     │
│               │                                                              │
│               ▼                                                              │
│      ┌─────────────────┐                                                    │
│      │ base_client.py  │                                                    │
│      └────────┬────────┘                                                    │
│               │                                                              │
│               ▼                                                              │
│         ┌──────────┐                                                        │
│         │ requests │                                                        │
│         └──────────┘                                                        │
│               │                                                              │
│               ▼                                                              │
│      ServiceNow REST API                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference - Key Connections

| From | To | Connection Type | Description |
|------|-----|-----------------|-------------|
| ESA Indexer | ServiceNowConnector | Interface Call | `load_from_checkpoint()` |
| ServiceNowConnector | EnhancedServiceNowClient | Composition | Client instance |
| EnhancedServiceNowClient | TableAPIClient | Inheritance | extends |
| TableAPIClient | BaseServiceNowClient | Inheritance | extends |
| BaseServiceNowClient | ServiceNow API | HTTP/REST | HTTPS requests |
| ServiceNowConnector | ESA Document | Transform | `_record_to_document()` |
| Credentials | OAuth Token | OAuth 2.0 | `/oauth_token.do` |
| Content Type | Tables | Mapping | `CONTENT_TYPE_TABLES` |
| Table | Field Config | Lookup | `TABLE_CONFIGS` |
