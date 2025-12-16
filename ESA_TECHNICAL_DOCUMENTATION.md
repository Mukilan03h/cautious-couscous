# ESA Technical Documentation

## 1. Executive Summary

ESA (Enterprise Search & Agents) is a comprehensive, open-source Generative AI and Enterprise Search platform. It is designed to connect to an organization's internal data sources (Google Drive, Slack, Confluence, GitHub, etc.), index that information, and provide a unified interface for searching and chatting with that data using Large Language Models (LLMs).

This documentation provides an in-depth technical overview of the ESA platform, covering its architecture, codebase structure, data pipelines, security mechanisms, and deployment strategies. It is intended for developers, architects, and system administrators who wish to understand the inner workings of ESA.

## 2. System Architecture

ESA follows a modular microservices-based architecture, primarily containerized using Docker.

### 2.1. High-Level Components

*   **Frontend (Web Server)**: A Next.js application serving the user interface.
*   **Backend (API Server)**: A FastAPI (Python) application handling API requests, business logic, and database interactions.
*   **Model Server**: A dedicated Python service for hosting local NLP models (embeddings, re-ranking) to avoid blocking the main API.
*   **Background Workers**: Asynchronous task processors (Celery) for document indexing, syncing, and maintenance.
*   **Relational Database**: PostgreSQL for persistent storage of application state (users, chats, connectors, configurations).
*   **Vector Database**: Vespa for high-performance vector similarity search and keyword search.
*   **Cache**: Redis for task queues (Celery broker) and caching user sessions/data.
*   **Object Storage**: MinIO (S3-compatible) for storing file uploads and other blobs.

### 2.2. Technology Stack

| Component | Technology | Version | Description |
| :--- | :--- | :--- | :--- |
| **Backend Language** | Python | 3.11+ | Core logic, API, Workers |
| **API Framework** | FastAPI | Latest | High-performance async web framework |
| **Frontend Framework** | Next.js | 15+ | React framework with App Router |
| **UI Library** | React | 19 | Component-based UI |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first CSS framework |
| **Relational DB** | PostgreSQL | 15+ | Primary data store |
| **Vector Engine** | Vespa | Latest | specialized vector & text search engine |
| **Task Queue** | Celery | Latest | Async background processing |
| **ORM** | SQLAlchemy | Latest | Database interaction |
| **Package Manager** | uv (Python), npm (Node) | - | Dependency management |

## 3. Backend Deep Dive (`backend/`)

The backend is the brain of ESA, handling data ingestion, search logic, and API responses. It is located in `backend/esa/`.

### 3.1. Directory Structure

*   `esa/auth/`: Authentication logic (OAuth, SAML, Basic).
*   `esa/chat/`: Chat session management, LLM interaction, and prompt handling.
*   `esa/connectors/`: Logic for connecting to external data sources (Slack, Google Drive, etc.).
*   `esa/db/`: Database models (SQLAlchemy) and engine configuration.
*   `esa/document_index/`: Interface for interacting with the Vespa vector database.
*   `esa/llm/`: Integration with LLM providers (OpenAI, Anthropic, LiteLLM, etc.).
*   `esa/server/`: FastAPI routers and endpoints.
*   `ee/`: Enterprise Edition specific features (RBAC, Analytics, specialized Auth).

### 3.2. Core Data Flow: Indexing Pipeline

The indexing pipeline is responsible for keeping the internal knowledge base in sync with external sources.

1.  **Polling/Pushing**: The `Docfetching` worker retrieves documents from configured connectors.
    *   *Polling*: Periodically checks for updates (e.g., Google Drive, Confluence).
    *   *Pushing*: Receives webhooks (e.g., Slack real-time events).
2.  **Processing**: The `Docprocessing` worker takes raw documents (PDF, HTML, DOCX) and:
    *   **Text Extraction**: Converts binary formats to plain text.
    *   **Chunking**: Splits text into manageable segments (chunks) to fit LLM context windows and improve retrieval precision. It uses smart strategies (recursive, semantic) to preserve context.
    *   **Metadata Extraction**: Extracts titles, authors, dates, and links.
3.  **Embedding**: Text chunks are sent to the **Model Server** (or external API) to generate vector embeddings (dense representations).
4.  **Indexing**: The processed chunks + embeddings + metadata are sent to **Vespa** for indexing.
5.  **Persistence**: Document status and mapping are stored in PostgreSQL to track sync state.

### 3.3. Search & RAG (Retrieval-Augmented Generation)

When a user asks a question:

1.  **Query Analysis**: The system analyzes the user's query to determine intent (search vs. chat) and extracts keywords.
2.  **Retrieval (Hybrid Search)**:
    *   **Semantic Search**: Uses the query embedding to find conceptually similar chunks in Vespa.
    *   **Keyword Search**: Uses BM25/keyword matching in Vespa for exact term matches.
    *   **Hybrid Fusion**: Combines results from both methods using a reciprocal rank fusion or weighted scoring.
3.  **Re-ranking**: Top results are passed through a cross-encoder (re-ranker) model to strictly order them by relevance to the query.
4.  **Context Construction**: The most relevant chunks are formatted into a prompt context window.
5.  **Generation**: The prompt (System Prompt + Context + User Query) is sent to the LLM.
6.  **Streaming Response**: The LLM's response is streamed back to the user token-by-token via Server-Sent Events (SSE).

### 3.4. Background Workers (Celery)

ESA uses a sophisticated multi-worker setup to ensure scalability and isolation.

*   **Primary Worker**: General orchestration.
*   **Docfetching Worker**: Dedicated to high-I/O tasks of fetching data from external APIs.
*   **Docprocessing Worker**: CPU-intensive tasks (parsing, chunking, embedding).
*   **Light Worker**: Fast, low-latency tasks (e.g., permissions sync, small metadata updates).
*   **Heavy Worker**: Long-running, resource-intensive maintenance tasks (e.g., index pruning).
*   **Beat**: Scheduler for periodic tasks (cron jobs).

*Configuration Note*: In smaller deployments, a "Lightweight Mode" consolidates these into a single process.

## 4. Frontend Deep Dive (`web/`)

The frontend is a modern React application built with Next.js.

### 4.1. Architecture

*   **App Router**: Uses Next.js 13+ App Router for efficient routing and server-side rendering (SSR).
*   **State Management**:
    *   **SWR**: For data fetching and caching (stale-while-revalidate).
    *   **Zustand**: For global client-side state (e.g., UI preferences, chat session state).
*   **Component Library**:
    *   **Radix UI**: Headless, accessible primitives for complex UI elements (Dialogs, Popovers).
    *   **Tailwind CSS**: For styling.
    *   **Tremor / Recharts**: For analytics and dashboards.

### 4.2. Key Directories

*   `src/app/`: Page routes and layouts.
    *   `src/app/chat/`: Main chat interface logic.
    *   `src/app/admin/`: Administration panel (Connectors, User Management).
*   `src/components/`: Reusable UI components.
*   `src/lib/`: Utility functions, API wrappers, and types.

## 5. Database & Storage Schema

### 5.1. PostgreSQL (Relational)
Stores the "Source of Truth" for application configuration.
*   `user`: User accounts and roles.
*   `connector`: Configurations for external data sources.
*   `credential`: Encrypted API keys and tokens for connectors.
*   `document`: Metadata about indexed documents (mappings to Vespa).
*   `chat_session`: History of user conversations.
*   `user_group`: (EE) Groups for RBAC.

### 5.2. Vespa (Vector)
Stores the actual searchable content.
*   **Schema**: Defines fields like `title`, `content`, `chunks`, `embeddings`, `metadata`.
*   **Rank Profiles**: Defines how search results are scored (e.g., `bm25`, `nativeRank`, `semantic`).

## 6. Security

*   **Authentication**: Supports built-in Basic Auth, Google OAuth, OIDC, and SAML (Enterprise).
*   **Access Control (RBAC)**:
    *   **Admins**: Full system access.
    *   **Curators**: Can manage knowledge/connectors but not system settings.
    *   **Basic Users**: Can search/chat.
*   **Document Permissions**:
    *   External permissions (e.g., "Only User A can see File X in Google Drive") are synced and enforced at search time.
    *   Vespa uses "Access Control Lists" (ACLs) attached to document chunks to filter results before they reach the LLM.
*   **Encryption**: Sensitive credentials (API keys) are encrypted at rest in Postgres using Fernet encryption.

## 7. Deployment

ESA is designed to be cloud-agnostic and container-native.

### 7.1. Docker Compose
The simplest way to run ESA. Orchestrates the following containers:
*   `web_server`: Frontend.
*   `api_server`: Backend API.
*   `background`: Celery workers.
*   `model_server`: Local inference.
*   `relational_db`: Postgres.
*   `index`: Vespa.
*   `cache`: Redis.
*   `minio`: Object storage.

### 7.2. Kubernetes (Helm)
For production scaling.
*   Separates stateless services (Web, API) from stateful ones (DBs).
*   Allows independent scaling of `docprocessing` workers based on ingestion load.

### 7.3. Environment Configuration
Configuration is handled via `.env` files or environment variables. Key variables:
*   `AUTH_TYPE`: `basic`, `google_oauth`, `oidc`, `saml`.
*   `POSTGRES_HOST`, `VESPA_HOST`, `REDIS_HOST`: Connection strings.
*   `OPENAI_API_KEY`: For LLM features (if using OpenAI).
*   `LOG_LEVEL`: Debugging verbosity.

## 8. Developer Guide

### 8.1. Prerequisites
*   Docker & Docker Compose
*   Python 3.11+
*   Node.js 22+

### 8.2. Setup Steps
1.  **Clone Repo**: `git clone ...`
2.  **Start Infrastructure**: `cd deployment/docker_compose && docker compose up -d relational_db index cache minio`
3.  **Backend Setup**:
    *   `cd backend`
    *   `uv sync` (Install dependencies)
    *   `alembic upgrade head` (Run Migrations)
    *   `python scripts/dev_run_background_jobs.py` (Start Workers)
    *   `uvicorn esa.main:app --reload` (Start API)
4.  **Frontend Setup**:
    *   `cd web`
    *   `npm install`
    *   `npm run dev`

### 8.3. Contribution
*   **Migrations**: Use `alembic revision -m "msg"` to create DB changes.
*   **Connectors**: Add new connectors in `backend/esa/connectors/`. Implement `Connector` and `ConnectorConfig` interfaces.
*   **Testing**:
    *   Unit: `pytest backend/tests/unit`
    *   Integration: `pytest backend/tests/integration`
    *   E2E: `npx playwright test` (in `web/`)

---
*Generated for ESA Technical Reference.*
