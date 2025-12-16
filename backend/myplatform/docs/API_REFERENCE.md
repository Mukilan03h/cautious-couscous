# MyPlatform API Reference

## Authentication

All API endpoints require authentication via JWT token.

```http
Authorization: Bearer <token>
```

---

## Tenants API

### Get Billing Information
```http
GET /api/myplatform/tenants/billing
```

**Response:**
```json
{
    "stripe_subscription_id": "sub_xxx",
    "status": "active",
    "current_period_start": "2024-01-01T00:00:00Z",
    "current_period_end": "2024-02-01T00:00:00Z",
    "number_of_seats": 10,
    "cancel_at_period_end": false
}
```

### Create Checkout Session
```http
POST /api/myplatform/tenants/billing/checkout-session
```

**Response:**
```json
{
    "session_id": "cs_xxx"
}
```

### Update Seat Count
```http
POST /api/myplatform/tenants/billing/update-seats
Content-Type: application/json

{
    "seats": 25
}
```

---

## User Groups API

### List Groups
```http
GET /api/myplatform/user-groups
```

**Response:**
```json
[
    {
        "id": 1,
        "name": "Engineering",
        "description": "Engineering team",
        "user_count": 15
    }
]
```

### Create Group
```http
POST /api/myplatform/user-groups
Content-Type: application/json

{
    "name": "Engineering",
    "description": "Engineering team"
}
```

### Get Group
```http
GET /api/myplatform/user-groups/{group_id}
```

### Update Group
```http
PUT /api/myplatform/user-groups/{group_id}
Content-Type: application/json

{
    "name": "Updated Name",
    "description": "Updated description"
}
```

### Delete Group
```http
DELETE /api/myplatform/user-groups/{group_id}
```

### Add User to Group
```http
POST /api/myplatform/user-groups/{group_id}/users
Content-Type: application/json

{
    "user_id": "uuid"
}
```

### Remove User from Group
```http
DELETE /api/myplatform/user-groups/{group_id}/users/{user_id}
```

---

## Analytics API

### Usage Summary
```http
GET /api/myplatform/analytics/usage-summary
```

**Response:**
```json
{
    "total_queries": 15000,
    "total_tokens": 500000,
    "active_users": 45,
    "total_users": 100
}
```

### Performance Metrics
```http
GET /api/myplatform/analytics/performance
```

**Response:**
```json
{
    "total_queries": 15000,
    "avg_response_time_ms": 250,
    "p95_response_time_ms": 500,
    "success_rate": 0.98,
    "active_users": 45,
    "total_tokens": 500000,
    "cache_hit_rate": 0.35,
    "indexed_documents": 10000
}
```

---

## OAuth Configurations API

### List Configurations
```http
GET /api/myplatform/oauth/configs
```

### Create Configuration
```http
POST /api/myplatform/oauth/configs
Content-Type: application/json

{
    "provider": "google",
    "client_id": "xxx.apps.googleusercontent.com",
    "client_secret": "xxx",
    "redirect_uri": "https://your-domain.com/callback",
    "enabled": true
}
```

### Update Configuration
```http
PUT /api/myplatform/oauth/configs/{config_id}
Content-Type: application/json

{
    "client_id": "new-client-id",
    "enabled": false
}
```

### Delete Configuration
```http
DELETE /api/myplatform/oauth/configs/{config_id}
```

### Toggle Configuration
```http
POST /api/myplatform/oauth/configs/{config_id}/toggle
```

---

## Reporting API

### Generate Usage Report
```http
POST /api/myplatform/reporting/usage-export/generate
Content-Type: application/json

{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "format": "csv"
}
```

**Response:**
```json
{
    "report_id": "report-uuid",
    "status": "generating"
}
```

### Get Reports
```http
GET /api/myplatform/reporting/usage-export
```

### Download Report
```http
GET /api/myplatform/reporting/usage-export/{report_id}/download
```

---

## Team Membership API

### List Members
```http
GET /api/myplatform/tenants/members
```

**Response:**
```json
[
    {
        "user_id": "uuid",
        "email": "user@company.com",
        "role": "admin",
        "status": "active",
        "is_admin": true
    }
]
```

### Get Member Count
```http
GET /api/myplatform/tenants/members/count
```

### Update Member Role
```http
PUT /api/myplatform/tenants/members/{user_id}/role
Content-Type: application/json

{
    "role": "admin"
}
```

### Remove Member
```http
DELETE /api/myplatform/tenants/members/{user_id}
```

---

## User Invitations API

### Create Invitation
```http
POST /api/myplatform/tenants/invitations
Content-Type: application/json

{
    "email": "newuser@company.com",
    "role": "user"
}
```

### List Invitations
```http
GET /api/myplatform/tenants/invitations
```

### Revoke Invitation
```http
DELETE /api/myplatform/tenants/invitations/{invite_id}
```
