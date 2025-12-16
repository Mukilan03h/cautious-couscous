# MyPlatform Module Index

Complete listing of all modules and their purposes.

## Root Level

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `main.py` | FastAPI application entry |

---

## Access Control (`access/`)

| File | Purpose |
|------|---------|
| `access.py` | Group-aware document ACL, user/group permission checks |

---

## Authentication (`auth/`)

| File | Purpose |
|------|---------|
| `users.py` | User authentication utilities |

---

## Background Tasks (`background/`)

### Celery Apps (`background/celery/apps/`)

| File | Purpose |
|------|---------|
| `background.py` | Default background worker |
| `heavy.py` | CPU-intensive tasks |
| `light.py` | Quick async tasks |
| `monitoring.py` | Health monitoring |
| `primary.py` | Main worker |

### Celery Tasks (`background/celery/tasks/`)

| Task Module | Purpose |
|-------------|---------|
| `cleanup/tasks.py` | Database cleanup |
| `cloud/tasks.py` | Cloud sync operations |
| `doc_permission_syncing/tasks.py` | Document permission sync |
| `external_group_syncing/tasks.py` | External group sync |
| `query_history/tasks.py` | Query history processing |
| `tenant_provisioning/tasks.py` | Tenant setup |
| `ttl_management/tasks.py` | TTL enforcement |
| `usage_reporting/tasks.py` | Usage report generation |

---

## Configuration (`configs/`)

| File | Purpose |
|------|---------|
| `app_configs.py` | All environment variables |

---

## Connectors (`connectors/`)

| File | Purpose |
|------|---------|
| `perm_sync_valid.py` | Permission sync validation |

---

## Database (`db/`)

| File | Purpose |
|------|---------|
| `analytics.py` | Analytics queries |
| `connector.py` | Connector operations |
| `connector_credential_pair.py` | CC pair operations |
| `connector_permissions.py` | Permission management |
| `document.py` | Document permissions |
| `document_set.py` | Document set privacy |
| `evals.py` | Evaluation data |
| `external_perm.py` | External permissions |
| `feature_flags.py` | Feature flag state |
| `permissions.py` | Permission queries |
| `persona.py` | Persona privacy |
| `query_history.py` | Query history data |
| `saml.py` | SAML accounts |
| `standard_answers.py` | Standard answers |
| `tenants.py` | Tenant data |
| `token_limits.py` | Token limit state |
| `usage_export.py` | Usage exports |
| `user_groups.py` | User group data |

---

## External Permissions (`external_permissions/`)

### Confluence

| File | Purpose |
|------|---------|
| `constants.py` | Confluence constants |
| `doc_sync.py` | Document sync |
| `group_sync.py` | Group sync |
| `page_access.py` | Page permissions |
| `space_access.py` | Space permissions |

### Google Drive

| File | Purpose |
|------|---------|
| `doc_sync.py` | Document sync |
| `folder_retrieval.py` | Folder permissions |
| `group_sync.py` | Group sync |
| `models.py` | Permission models |
| `permission_retrieval.py` | Permission fetch |

### Jira

| File | Purpose |
|------|---------|
| `doc_sync.py` | Issue sync |
| `group_sync.py` | Group sync |
| `models.py` | Permission models |
| `page_access.py` | Project permissions |

### Slack

| File | Purpose |
|------|---------|
| `channel_access.py` | Channel permissions |
| `doc_sync.py` | Message sync |
| `group_sync.py` | User group sync |
| `utils.py` | Slack utilities |

---

## Feature Flags (`feature_flags/`)

| File | Purpose |
|------|---------|
| `factory.py` | Provider factory |
| `posthog_provider.py` | PostHog integration |

---

## Server API (`server/`)

### Analytics (`server/analytics/`)
- `api.py` - Usage and performance endpoints

### Billing (`server/billing/`)
- `api.py` - Stripe billing endpoints

### Tenants (`server/tenants/`)
- `api.py` - Tenant management
- `access.py` - JWT token generation
- `billing.py` - Billing operations
- `billing_api.py` - Billing endpoints
- `models.py` - Request/response models
- `product_gating.py` - Feature gating (ALL ENABLED)
- `provisioning.py` - Tenant provisioning
- `team_membership_api.py` - Team management
- `user_invitations_api.py` - Invitations
- `user_mapping.py` - User-tenant mapping

### User Groups (`server/user_group/`)
- `api.py` - CRUD endpoints
- `models.py` - Request/response models

### OAuth (`server/oauth/`)
- `configs_api.py` - OAuth configuration management

### Reporting (`server/reporting/`)
- `usage_export_api.py` - Report generation
- `usage_export_generation.py` - Report creation

---

## Tests (`tests/`)

| File | Coverage |
|------|----------|
| `test_access.py` | Access control |
| `test_background.py` | Background tasks |
| `test_configs.py` | Configuration |
| `test_db.py` | Database operations |
| `test_external_permissions.py` | Permission sync |
| `test_feature_flags.py` | Feature flags |
| `test_server_api.py` | API endpoints |
| `test_tenants.py` | Tenant management |
