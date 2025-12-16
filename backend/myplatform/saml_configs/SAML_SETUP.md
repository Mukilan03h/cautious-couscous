# SAML SSO Setup Guide

SAML is already included in the MIT-licensed ESA CE code. No additional implementation needed!

## Quick Start

1. Set auth type in `.env`:
   ```bash
   AUTH_TYPE=saml
   ```

2. Copy and configure your IdP settings:
   ```bash
   # For Okta
   cp myplatform/saml_configs/okta.settings.json esa/configs/saml_config/settings.json
   
   # For Azure AD
   cp myplatform/saml_configs/azure_ad.settings.json esa/configs/saml_config/settings.json
   ```

3. Edit `settings.json` with your IdP values

---

## Okta Setup

1. Create SAML app in Okta Admin Console
2. Set these values:
   - **Single Sign-On URL**: `https://YOUR_DOMAIN/api/auth/saml/callback`
   - **Audience URI**: `https://YOUR_DOMAIN/api/auth/saml/callback`
   - **Attribute Statements**: `email` → `user.email`

3. Copy from Okta to `settings.json`:
   - IdP SSO URL → `idp.singleSignOnService.url`
   - IdP Entity ID → `idp.entityId`
   - X.509 Certificate → `idp.x509cert`

---

## Azure AD / Entra ID Setup

1. Register enterprise app in Azure Portal
2. Set these values:
   - **Identifier (Entity ID)**: `https://YOUR_DOMAIN/api/auth/saml/callback`
   - **Reply URL**: `https://YOUR_DOMAIN/api/auth/saml/callback`

3. Copy from Azure to `settings.json`:
   - Login URL → `idp.singleSignOnService.url`
   - Azure AD Identifier → `idp.entityId`  
   - Certificate (Base64) → `idp.x509cert`

---

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/auth/saml/authorize` | Initiates SAML login |
| `POST /api/auth/saml/callback` | Receives SAML response |
| `POST /api/auth/saml/logout` | SAML logout |

---

## Frontend Login URL

Redirect users to: `/auth/saml?next=/`
