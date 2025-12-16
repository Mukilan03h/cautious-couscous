# ESA AI Platform - Features Overview

> **ESA** is a feature-rich, self-hostable Chat UI that works with any LLM. It is easy to deploy and can run in a completely air-gapped environment.

---

## 🤖 Custom Agents

Build AI Agents with unique instructions, knowledge, and actions.

- **Persona Configuration**: Define custom system prompts and personalities
- **Knowledge Binding**: Attach specific document sets to each agent
- **Action Capabilities**: Connect agents to external tools and APIs
- **Multi-Agent Workflows**: Create specialized agents for different use cases

---

## 🌍 Web Search

Browse the web with multiple search providers:

- **Google PSE** (Programmable Search Engine)
- **Exa** - AI-powered semantic search
- **Serper** - Google Search API alternative
- **Built-in Scraper** for content extraction
- **Firecrawl** integration for advanced web crawling

---

## 🔍 RAG (Retrieval-Augmented Generation)

Best-in-class hybrid search + knowledge graph:

- **Hybrid Search**: Combines vector similarity with keyword matching
- **Knowledge Graph**: Understands relationships between documents
- **File Support**: PDF, DOCX, TXT, HTML, Markdown, and more
- **Chunking Strategies**: Intelligent document splitting for optimal retrieval
- **Re-ranking**: ML-based result re-ordering for relevance

---

## 🔄 Connectors (40+ Integrations)

Pull knowledge, metadata, and access information from external applications:

### Productivity & Collaboration
- **Slack** - Channels, threads, and DMs
- **Microsoft Teams** - Messages and files
- **Notion** - Pages, databases, and blocks
- **Confluence** - Spaces and pages
- **Google Drive** - Docs, Sheets, Slides
- **OneDrive / SharePoint** - Files and folders
- **Dropbox** - Cloud file storage

### Development & Engineering
- **GitHub** - Repos, issues, PRs, wikis
- **GitLab** - Projects and merge requests
- **Jira** - Issues and project boards
- **Linear** - Issues and cycles
- **Stack Overflow for Teams**

### Customer & Communication
- **Zendesk** - Tickets and knowledge base
- **Freshdesk** - Support tickets
- **Intercom** - Conversations
- **HubSpot** - CRM data

### Documentation & Knowledge
- **Guru** - Knowledge cards
- **BookStack** - Books and chapters
- **MediaWiki** - Wiki pages
- **ReadTheDocs** - Documentation

### Data & Business
- **Salesforce** - CRM objects
- **Looker** - Dashboards and looks
- **BigQuery** - SQL queries
- **Snowflake** - Data warehouse

### Web & Custom
- **Web Scraper** - Any public URL
- **Sitemap Crawler** - Bulk URL ingestion
- **File Upload** - Direct document upload
- **API Connector** - Custom REST integrations

---

## 🔬 Deep Research

Get in-depth answers with agentic multi-step search:

- **Iterative Query Refinement**: Automatically expands searches based on initial findings
- **Cross-Source Synthesis**: Combines information from multiple documents
- **Citation Generation**: Provides inline references to source material
- **Follow-up Suggestions**: Proposes related questions for deeper exploration

---

## ▶️ Actions & MCP (Model Context Protocol)

Give AI Agents the ability to interact with external systems:

- **Built-in Actions**: 
  - Web search
  - Document retrieval
  - Image generation
  - Code execution
  
- **Custom Actions**: Define your own API integrations
- **MCP Server**: Expose ESA capabilities to external MCP clients
- **Webhook Support**: Trigger external workflows

---

## 💻 Code Interpreter

Execute code to analyze data, render graphs, and create files:

- **Python Runtime**: Sandboxed code execution
- **Data Analysis**: pandas, numpy, scipy support
- **Visualization**: matplotlib, plotly charts
- **File Generation**: Create CSVs, images, documents
- **Security**: Docker-isolated execution environment

---

## 🎨 Image Generation

Generate images based on user prompts:

- **DALL-E Integration**: OpenAI image generation
- **Stable Diffusion**: Self-hosted options
- **Inline Display**: Images shown directly in chat
- **Prompt Enhancement**: AI-assisted prompt optimization

---

## 👥 Collaboration Features

Enterprise-ready team functionality:

### Chat & Sharing
- **Chat Sharing**: Share conversations with teammates
- **Chat History**: Searchable conversation archives
- **Feedback Collection**: Thumbs up/down on responses
- **Export Options**: Download chats as JSON/Markdown

### User Management
- **Role-Based Access**: Admin, Curator, Basic user roles
- **SSO Integration**: OIDC, SAML, OAuth2 support
- **User Groups**: Organize users into teams
- **Invite System**: Email-based user invitations

### Analytics & Monitoring
- **Usage Dashboard**: Track queries, users, and costs
- **LLM Cost Tracking**: Monitor token usage per model
- **Query Analytics**: Understand search patterns
- **Response Quality Metrics**: Track feedback trends

---

## 🔒 Security & Enterprise Features

Built for teams of all sizes:

### Authentication
- **SSO Support**: OIDC, SAML 2.0, OAuth2
- **Multi-Factor Authentication** (via SSO provider)
- **Session Management**: Configurable timeouts
- **API Key Management**: Secure programmatic access

### Access Control
- **Document Permissioning**: Mirrors source system permissions
- **Connector-Level ACLs**: Control who sees what data
- **Admin-Only Connectors**: Restrict sensitive integrations
- **Curator Role**: Manage knowledge without admin access

### Data Security
- **Credential Encryption**: Secrets stored encrypted at rest
- **Air-Gapped Deployment**: No external network required
- **On-Premise Option**: Full data sovereignty
- **Audit Logging**: Track all user actions

---

## 🏗️ Architecture & Deployment

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python (FastAPI) |
| **Frontend** | Next.js / TypeScript |
| **Database** | PostgreSQL |
| **Vector Search** | Vespa |
| **Caching** | Redis |
| **File Storage** | MinIO (S3-compatible) |
| **NLP Models** | Hugging Face (local) |
| **Proxy** | Nginx |

### Deployment Options

- **Docker Compose**: Single-server deployment
- **Kubernetes/Helm**: Scalable cluster deployment
- **Terraform**: Infrastructure as code
- **Cloud Guides**: AWS EKS, Azure VMs, GCP

### LLM Compatibility

Works with all major providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3, Claude 2)
- Google (Gemini Pro)
- Azure OpenAI
- AWS Bedrock
- Ollama (local models)
- vLLM (self-hosted)
- LiteLLM proxy (any provider)

---

## 📊 Scalability

Designed for enterprise scale:

- **Document Volume**: Supports tens of millions of documents
- **Concurrent Users**: Handles high query loads
- **Horizontal Scaling**: Add more workers as needed
- **Background Processing**: Async document indexing
- **Model Server Separation**: Dedicated inference infrastructure

---

## 📚 Licensing

| Edition | License | Features |
|---------|---------|----------|
| **Community (CE)** | MIT (Free) | Full core functionality |
| **Enterprise (EE)** | Commercial | SSO, RBAC, Analytics, Support |

---

## 🛠️ Building on Enterprise Features

### Can You Extend EE Features?

**Yes, with conditions:**

| Scenario | Allowed? |
|----------|----------|
| Development & Testing | ✅ Yes (free) |
| Internal Prototyping | ✅ Yes (free) |
| Production Deployment | ⚠️ Requires ESA Enterprise License |
| Contributing Back | ✅ Yes (PRs welcome) |

### Enabling Enterprise Features Locally

Set in your `.env` file:
```bash
ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true
AUTH_TYPE=basic  # or oidc, saml, google_oauth
```

### EE Codebase Structure

```
backend/ee/esa/
├── auth/              # SSO authentication logic
├── access/            # Access control utilities
├── server/
│   ├── analytics/     # Usage analytics API
│   ├── user_group/    # RBAC user groups
│   ├── query_history/ # Query tracking
│   ├── reporting/     # Usage export API
│   ├── oauth/         # OAuth token management
│   ├── enterprise_settings/  # EE config API
│   └── token_rate_limits/    # Rate limiting
├── external_permissions/  # Document ACLs
└── main.py            # EE FastAPI app entry
```

### Key Extension Points

#### 1. SSO Integration
**Files:** `backend/esa/configs/app_configs.py`

| Auth Type | Environment Variables |
|-----------|----------------------|
| OIDC | `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OPENID_CONFIG_URL` |
| SAML | `SAML_CONF_DIR` (point to config directory) |
| Google | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` |

#### 2. RBAC (User Groups)
**Files:** `backend/ee/esa/server/user_group/`

- Create groups via API: `POST /api/manage/admin/user-group`
- Assign users to groups
- Restrict document sets and assistants to groups

#### 3. Analytics API
**Files:** `backend/ee/esa/server/analytics/api.py`

Endpoints for:
- Daily query counts
- Query performance metrics
- User engagement stats
- LLM token usage

#### 4. Query History
**Files:** `backend/ee/esa/server/query_history/`

- View all user queries (admin)
- Export query logs
- Configurable via `ONYX_QUERY_HISTORY_TYPE`

#### 5. Usage Reporting
**Files:** `backend/ee/esa/server/reporting/usage_export_api.py`

- Export usage data as CSV/JSON
- Token spend tracking
- Per-user/per-group analytics

### Custom Extension Example

To add a new analytics endpoint:

```python
# backend/ee/esa/server/analytics/api.py
from fastapi import APIRouter, Depends
from esa.auth.users import current_admin_user

router = APIRouter(prefix="/admin/analytics")

@router.get("/custom-metric")
def get_custom_metric(
    user=Depends(current_admin_user)
):
    # Your custom analytics logic
    return {"metric": "value"}
```

### License Considerations

Per the EE License (`backend/ee/LICENSE`):

> You may copy and modify the Software for **development and testing purposes**, without requiring a subscription.

> Production use requires a valid **ESA Enterprise license**.

**For commercial production use**, contact ESA at https://esa.app/pricing

---

## 🔗 Resources

- **Documentation**: https://docs.esa.app
- **GitHub**: https://github.com/esa-dot-app/esa
- **Discord**: https://discord.gg/TDJ59cGV2X
- **Website**: https://esa.app
