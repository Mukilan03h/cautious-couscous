# MyPlatform - Enterprise Features as Free Platform

## Overview

MyPlatform is a **complete port of all Enterprise Edition (EE) features** to a free, self-hosted platform. This migration ensures **100% feature parity** with the original EE module, with no license restrictions.

## File Statistics

| Metric | EE (Original) | MyPlatform |
|--------|-------------:|----------:|
| **Python Files** | 132 | **176+** ✅ |
| **Root Modules** | 12 | **16** ✅ |
| **Server Modules** | 13 | **18** ✅ |
| **DB Modules** | 14 | **18** ✅ |
| **Test Files** | 0 | **8** ✅ |

## Directory Structure

```
myplatform/
├── access/                 # Group-aware ACL (2 files)
├── auth/                   # Authentication (2 files)
├── background/             # Celery tasks (30 files)
│   └── celery/
│       ├── apps/           # Worker configurations
│       └── tasks/          # Background jobs
│           ├── cleanup/
│           ├── cloud/
│           ├── doc_permission_syncing/
│           ├── external_group_syncing/
│           ├── query_history/
│           ├── tenant_provisioning/
│           ├── ttl_management/
│           └── usage_reporting/
├── configs/                # Environment configs (2 files)
├── connectors/             # Permission sync validation (2 files)
├── db/                     # Database operations (18 files)
├── document_index/         # Vespa ACL filters (4 files)
├── external_permissions/   # Connector permissions (29 files)
│   ├── confluence/
│   ├── github/
│   ├── gmail/
│   ├── google_drive/
│   ├── jira/
│   ├── salesforce/
│   ├── sharepoint/
│   ├── slack/
│   └── teams/
├── feature_flags/          # PostHog integration (3 files)
├── hooks/                  # System hooks (5 files)
├── esabot/                # Slack bot handlers (4 files)
├── saml_configs/           # SAML configuration (3 files)
├── server/                 # API endpoints (50+ files)
│   ├── analytics/
│   ├── billing/
│   ├── connector_sync/
│   ├── enterprise_settings/
│   ├── evals/
│   ├── feature_flags/
│   ├── middleware/
│   ├── oauth/
│   ├── permissions/
│   ├── query_and_chat/
│   ├── query_history/
│   ├── rbac/
│   ├── reporting/
│   ├── standard_answers/
│   ├── tenants/
│   ├── token_limits/
│   └── user_group/
├── tests/                  # Test suite (8 files)
├── utils/                  # Utilities (4 files)
└── main.py                 # Application entry point
```

## Key Enterprise Features

### 1. Multi-Tenant Architecture
- Tenant provisioning and management
- Per-tenant billing via Stripe
- Team invitations and membership
- Tenant isolation

### 2. Permission Synchronization
- Google Drive permissions
- Confluence space/page permissions
- Slack channel permissions  
- Jira project permissions
- GitHub repository permissions
- SharePoint site permissions
- Microsoft Teams permissions
- Salesforce permissions

### 3. User Management
- User groups with CRUD API
- Role-based access control (RBAC)
- Token rate limiting per user/group
- SSO via SAML

### 4. Analytics & Reporting
- Query history tracking
- Usage reports generation
- Performance metrics
- Token usage analytics

### 5. Feature Flags
- PostHog integration
- A/B testing support
- Feature gating (ALL ENABLED)

### 6. Document Access Control
- Group-aware ACL
- External user/group permissions
- Document-level security
- Vespa ACL filters

## No Feature Gating

```python
# All enterprise features are FREE
def is_feature_gated(feature_name: str) -> bool:
    return False  # Always enabled!
```

## Running Tests

```bash
cd backend
pytest myplatform/tests/ -v
```

## Environment Variables

See `configs/app_configs.py` for all configuration options:

| Variable | Description |
|----------|------------|
| `STRIPE_SECRET_KEY` | Stripe API key for billing |
| `STRIPE_PRICE_ID` | Stripe price plan ID |
| `POSTHOG_API_KEY` | PostHog analytics key |
| `WEB_DOMAIN` | Base URL for redirects |
| `DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY` | Permission sync interval |

## Migration Notes

- All imports use `myplatform.*` namespace (no `ee.esa` dependencies)
- All features are fully functional without license restrictions
- Original EE code preserved in `backend/ee/` for reference only
