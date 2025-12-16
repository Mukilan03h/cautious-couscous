# MyPlatform Developer Documentation

## Architecture Overview

MyPlatform is a modular enterprise platform ported from the EE (Enterprise Edition) codebase. All enterprise features are available without license restrictions.

## Module Structure

### Core Modules

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `access/` | Document ACL | `access.py` |
| `auth/` | Authentication | `users.py` |
| `db/` | Database operations | 18 models |
| `server/` | API endpoints | 50+ files |

### Background Processing

```
background/celery/
├── apps/           # Celery worker configs
│   ├── background.py
│   ├── heavy.py
│   ├── light.py
│   ├── monitoring.py
│   └── primary.py
└── tasks/          # Background jobs
    ├── doc_permission_syncing/
    ├── external_group_syncing/
    ├── tenant_provisioning/
    └── usage_reporting/
```

### External Permissions

Permission sync for all connectors:

| Connector | Files | Capabilities |
|-----------|-------|--------------|
| Confluence | 4 | Space/page ACL |
| Google Drive | 4 | Folder/file perms |
| Jira | 3 | Project perms |
| Slack | 4 | Channel access |
| SharePoint | 3 | Site permissions |
| GitHub | 3 | Repo access |
| Teams | 2 | Channel perms |

## API Reference

### Tenant Management

```python
# Create tenant
POST /api/myplatform/tenants
{
    "email": "admin@company.com",
    "referral_source": "organic"
}

# Get billing info
GET /api/myplatform/tenants/billing

# Update seats
POST /api/myplatform/tenants/billing/update-seats
{
    "seats": 25
}
```

### User Groups

```python
# List groups
GET /api/myplatform/user-groups

# Create group
POST /api/myplatform/user-groups
{
    "name": "Engineering",
    "description": "Engineering team"
}

# Add user to group
POST /api/myplatform/user-groups/{group_id}/users
{
    "user_id": "user-uuid"
}
```

### Analytics

```python
# Usage summary
GET /api/myplatform/analytics/usage-summary

# Performance metrics
GET /api/myplatform/analytics/performance
```

### OAuth Configurations

```python
# List OAuth configs
GET /api/myplatform/oauth/configs

# Create OAuth config
POST /api/myplatform/oauth/configs
{
    "provider": "google",
    "client_id": "...",
    "client_secret": "...",
    "redirect_uri": "..."
}
```

## Database Models

### Key Models

| Model | Table | Purpose |
|-------|-------|---------|
| `Document` | documents | Document metadata |
| `UserGroup` | user_groups | Group management |
| `DocumentSet` | document_sets | Document collections |
| `Persona` | personas | AI personas |
| `SamlAccount` | saml_accounts | SAML sessions |

### Permission Models

```python
from myplatform.db.document import upsert_document_external_perms

# Set document permissions
upsert_document_external_perms(
    db_session=session,
    doc_id="doc123",
    external_access=ExternalAccess(
        external_user_emails={"user@company.com"},
        external_user_group_ids={"engineering"},
        is_public=False,
    ),
    source_type=DocumentSource.GOOGLE_DRIVE,
)
```

## Feature Flags

```python
from myplatform.feature_flags.factory import get_feature_flag_provider

provider = get_feature_flag_provider()
if provider:
    enabled = provider.is_enabled("new_feature", user_id="user123")
```

## Testing

```bash
# Run all tests
pytest myplatform/tests/ -v

# Run specific module tests
pytest myplatform/tests/test_db.py -v
pytest myplatform/tests/test_access.py -v

# Run with coverage
pytest myplatform/tests/ --cov=myplatform
```

## Configuration

### Required Environment Variables

```bash
# Stripe Integration
STRIPE_SECRET_KEY=sk_xxx
STRIPE_PRICE_ID=price_xxx

# PostHog Analytics
POSTHOG_API_KEY=phc_xxx
POSTHOG_HOST=https://us.i.posthog.com

# Application
WEB_DOMAIN=https://your-domain.com
```

### Permission Sync Frequencies

```python
# Default: 5 minutes
DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY = 300

# Confluence: 30 minutes
CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY = 1800

# Google Drive: 5 minutes
GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY = 300
```

## Migration from EE

The migration is complete:
- 176 Python files in myplatform
- All imports use `myplatform.*` namespace
- No `ee.esa` dependencies
- All features enabled (no gating)
