# ESA Technical Architecture & Implementation Specification

This document serves as the authoritative technical reference for the ESA (formerly Onyx/Danswer) platform. It details the system architecture, data models, configuration options, and internal algorithms with granular precision. It is intended for core developers and system architects.

---

## 1. System Architecture

The platform is built as a distributed system comprising several distinct services, orchestrated via Docker Compose or Kubernetes.

### 1.1. Service Components

| Component | Technology Stack | Responsibilities |
| :--- | :--- | :--- |
| **Web Frontend** | Next.js 15+ (App Router), React 18, Tailwind CSS, SWR | Renders the User Interface (Chat, Admin, Settings). Handles client-side state and data fetching. Communicates exclusively with the Backend API. |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, Pydantic | Exposes RESTful endpoints. Handles Authentication, Session Management, Chat Orchestration, and Management Logic. |
| **Primary Worker** | Python, Celery, Redis | Handles lightweight background tasks: Connector scheduling, Signal checking, Maintenance coordination. |
| **DocFetching Worker** | Python, Celery, Multiprocessing | Dedicated worker for I/O bound tasks. Fetches documents from external APIs (Google, Slack, etc.). Runs connectors in isolated processes. |
| **DocProcessing Worker** | Python, Celery, PyTorch/ONNX | Dedicated worker for CPU/GPU bound tasks. Handles Chunking, Embedding, and Indexing documents into Vespa. |
| **Light Worker** | Python, Celery | Handles high-frequency, low-latency tasks such as permission syncing and metadata updates. |
| **Heavy Worker** | Python, Celery | Handles long-running maintenance tasks such as index pruning or bulk updates. |
| **PostgreSQL** | PostgreSQL 15+ | Primary relational store. Sources of truth for Users, Permissions, Connectors, Chat History, and Indexing State. |
| **Vespa** | Vespa (Java/C++) | Vector Database and Search Engine. Stores document embeddings, content, and metadata. Handles Hybrid Search and Ranking. |
| **Redis** | Redis 7+ | In-memory data store. Functions as the Celery Message Broker, Cache, Distributed Lock Manager, and Pub/Sub channel. |
| **MinIO / S3** | MinIO / AWS S3 | Object storage. Stores intermediate document batches, user uploads, and connector state checkpoints. |
| **Model Server** | Python / Triton | Dedicated inference service for hosting Embedding Models (Bi-Encoders) and Reranking Models (Cross-Encoders). |

### 1.2. Communication Patterns

1.  **Frontend -> Backend**: REST API (JSON) + Server-Sent Events (SSE) for streaming chat responses.
2.  **Backend -> Workers**: Asynchronous task dispatch via Redis (Celery Broker).
3.  **Workers -> Database**: SQLAlchemy (Sync/Async) for Postgres access.
4.  **Workers -> Vespa**: HTTP/2 API for document feeding and querying.
5.  **Workers -> Model Server**: HTTP/REST for embedding generation.
6.  **Inter-Worker**: Redis Pub/Sub for stop signals (e.g., halting a chat generation).

---

## 2. Data Model Specification (PostgreSQL)

The relational schema is defined using SQLAlchemy ORM.

### 2.1. Authentication & Users

#### `user` Table
*   `id` (UUID): Primary Key.
*   `email` (String): Normalized email address.
*   `role` (Enum):
    *   `BASIC`: Standard user. Can chat and manage own sessions.
    *   `ADMIN`: Full system access. Can manage connectors and users.
    *   `CURATOR`: Can manage document sets and prompts.
*   `preferences` (JSONB): UI preferences (theme, auto-scroll).
*   `is_active` (Boolean): Soft deletion flag.
*   `oidc_expiry` (DateTime): Expiration time for OIDC sessions.

#### `oauth_account` Table
*   `id` (UUID): Primary Key.
*   `user_id` (FK -> user.id): The user who owns this account.
*   `provider` (String): Identity provider name (e.g., `google`, `github`, `oidc`).
*   `access_token` (Text): Encrypted access token.
*   `refresh_token` (Text): Encrypted refresh token.
*   `expires_at` (Int): Token expiration timestamp.

#### `user_group` Table (Enterprise)
*   `id` (Int): Primary Key.
*   `name` (String): Unique group name.
*   `is_up_to_date` (Boolean): Sync status flag.
*   `cc_pairs` (M2M): Connectors accessible to this group.

### 2.2. Connectors & Ingestion

#### `connector` Table
*   `id` (Int): Primary Key.
*   `name` (String): Human-readable name.
*   `source` (Enum): The data source type (e.g., `GOOGLE_DRIVE`, `SLACK`, `WEB`, `CONFLUENCE`).
*   `connector_specific_config` (JSONB): JSON blob containing source-specific settings (e.g., `{"site_url": "..."}`).
*   `refresh_freq` (Int): Seconds between incremental syncs.
*   `prune_freq` (Int): Seconds between prune runs.

#### `credential` Table
*   `id` (Int): Primary Key.
*   `credential_json` (Encrypted JSON): Stores API keys, tokens, or service account details.
*   `user_id` (FK -> user.id): The user who added the credential.
*   `admin_public` (Boolean): Whether other admins can use this credential.

#### `connector_credential_pair` ("CC Pair") Table
*   `id` (Int): Primary Key.
*   `connector_id` (FK -> connector.id).
*   `credential_id` (FK -> credential.id).
*   `name` (String): User-defined name for this instance.
*   `status` (Enum): `ACTIVE`, `PAUSED`, `FAILING`, `DELETING`.
*   `last_successful_index_time` (DateTime): Timestamp of the last successful incremental sync.
*   `total_docs_indexed` (Int): Counter of documents currently indexed.
*   `access_type` (Enum): `PUBLIC` (visible to all), `PRIVATE` (requires permissions).

#### `index_attempt` Table
*   `id` (Int): Primary Key.
*   `connector_credential_pair_id` (FK).
*   `status` (Enum): `NOT_STARTED`, `IN_PROGRESS`, `SUCCESS`, `FAILED`, `PARTIAL_SUCCESS`.
*   `time_created` (DateTime): Job creation time.
*   `time_updated` (DateTime): Last status update.
*   `total_batches` (Int): Total document batches identified.
*   `completed_batches` (Int): Number of batches processed.
*   `new_docs_indexed` (Int): Count of new docs added.
*   `error_msg` (Text): High-level error description.
*   `full_exception_trace` (Text): Detailed traceback.

### 2.3. Documents & Indexing

#### `document` Table
*   `id` (String): Unique Identifier (URL or Source ID).
*   `semantic_id` (String): Human-readable title or name.
*   `doc_updated_at` (DateTime): Modification timestamp from the source system.
*   `link` (String): Direct URL to the document.
*   `boost` (Int): Manual relevance boost score.
*   `hidden` (Boolean): If true, excluded from search results.
*   `access_control_list` (Array[String]): List of emails/groups allowed to view this document.

#### `chunk_stats` Table
*   `id` (String): Unique Chunk ID (DocumentID + ChunkIndex).
*   `document_id` (FK -> document.id).
*   `chunk_in_doc_id` (Int): Index of the chunk within the document.
*   `information_content_boost` (Float): AI-computed information density score.

### 2.4. Chat & Agents

#### `persona` Table
*   `id` (Int): Primary Key.
*   `name` (String): Assistant name.
*   `description` (String): Assistant description.
*   `system_prompt` (Text): The base prompt instructions.
*   `num_chunks` (Float): Default retrieval setting.
*   `tools` (M2M): Linked `tool` records.
*   `document_sets` (M2M): Linked `document_set` records.

#### `chat_session` Table
*   `id` (UUID): Primary Key.
*   `user_id` (FK -> user.id).
*   `persona_id` (FK -> persona.id).
*   `description` (Text): Title of the conversation.
*   `deleted` (Boolean): Soft deletion flag.

#### `chat_message` Table
*   `id` (Int): Primary Key.
*   `chat_session_id` (FK -> chat_session.id).
*   `message_type` (Enum): `USER`, `ASSISTANT`, `SYSTEM`, `TOOL_CALL`, `TOOL_CALL_RESPONSE`.
*   `message` (Text): The content.
*   `token_count` (Int): Number of tokens in the message.
*   `citations` (JSONB): Map of citation markers to `SearchDoc` IDs.
*   `files` (JSONB): Metadata of attached files.

#### `tool_call` Table
*   `id` (Int): Primary Key.
*   `chat_message_id` (FK): The assistant message that triggered this call.
*   `tool_name` (String): e.g., `internal_search`.
*   `tool_arguments` (JSONB): Arguments passed to the tool.
*   `tool_response` (Text): The raw output from the tool.

---

## 3. Configuration Reference

The system is configured via Environment Variables.

### 3.1. Core Application Config
*   `APP_HOST`, `APP_PORT`: Bind address and port (default `0.0.0.0:8080`).
*   `WEB_DOMAIN`: The public URL of the frontend (used for OAuth redirects).
*   `AUTH_TYPE`: `basic`, `google_oauth`, `oidc`, `saml`, or `disabled`.
*   `DISABLE_GENERATIVE_AI`: If true, disables LLM features (Search only mode).

### 3.2. Database & Infrastructure
*   `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
*   `VESPA_HOST`, `VESPA_PORT`, `VESPA_TENANT_PORT`.
*   `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`.
*   `S3_ENDPOINT_URL`, `S3_AWS_ACCESS_KEY_ID`, `S3_AWS_SECRET_ACCESS_KEY`, `S3_FILE_STORE_BUCKET_NAME`.

### 3.3. LLM & Embedding Config
*   `GEN_AI_MODEL_PROVIDER`: `openai`, `anthropic`, `azure`, `bedrock`, `custom`.
*   `GEN_AI_API_KEY`: API Key for the provider.
*   `GEN_AI_MODEL_VERSION`: Default model (e.g., `gpt-4o`).
*   `FAST_GEN_AI_MODEL_VERSION`: Faster model for auxiliary tasks (e.g., `gpt-4o-mini`).
*   `DOCUMENT_ENCODER_MODEL`: HuggingFace model path (default: `nomic-ai/nomic-embed-text-v1`).
*   `DOC_EMBEDDING_DIM`: Dimension of vectors (default: `768`).
*   `ENABLE_CONTEXTUAL_RAG`: Enable document-context generation (default: `false`).

### 3.4. Celery Worker Config
*   `CELERY_WORKER_PRIMARY_CONCURRENCY`: Threads for primary worker.
*   `CELERY_WORKER_DOCFETCHING_CONCURRENCY`: Parallel connector jobs.
*   `CELERY_WORKER_DOCPROCESSING_CONCURRENCY`: Parallel indexing jobs.
*   `CELERY_WORKER_LIGHT_CONCURRENCY`: Threads for light tasks.

---

## 4. Connector Catalog

The system supports a wide range of connectors, defined in `backend/esa/connectors/registry.py`.

| Source | Class Name | Description |
| :--- | :--- | :--- |
| **Web** | `WebConnector` | Crawls websites. Supports sitemaps and recursive crawling. |
| **File** | `LocalFileConnector` | Indexes local files uploaded by users. |
| **Slack** | `SlackConnector` | Indexes Channels, Threads, and Messages. |
| **Google Drive** | `GoogleDriveConnector` | Indexes Docs, Sheets, Slides, PDFs in Drive. |
| **Github** | `GithubConnector` | Indexes Repositories, Issues, Pull Requests. |
| **Confluence** | `ConfluenceConnector` | Indexes Spaces, Pages, Blog Posts. |
| **Jira** | `JiraConnector` | Indexes Issues, Projects, Comments. |
| **Notion** | `NotionConnector` | Indexes Pages and Databases. |
| **Sharepoint** | `SharepointConnector` | Indexes Sites and Documents. |
| **Salesforce** | `SalesforceConnector` | Indexes CRM objects (Accounts, Contacts, Opportunities). |
| **Zendesk** | `ZendeskConnector` | Indexes Tickets and Help Center Articles. |
| **Gmail** | `GmailConnector` | Indexes Emails and Attachments. |
| **Gitlab** | `GitlabConnector` | Indexes Projects, MRs, Issues. |
| **Dropbox** | `DropboxConnector` | Indexes Files and Folders. |
| **Teams** | `TeamsConnector` | Indexes Teams Channels and Messages. |
| **HubSpot** | `HubSpotConnector` | Indexes CRM data. |
| **Linear** | `LinearConnector` | Indexes Issues and Projects. |
| **Wiki/MediaWiki** | `WikipediaConnector` | Indexes Wiki pages. |
| **S3/Blob** | `BlobStorageConnector` | Indexes files in buckets. |

---

## 5. Ingestion Pipeline Implementation

The ingestion process is the "Write Path" of the system.

### 5.1. Scheduling Logic (`check_for_indexing`)
*   **Type**: Periodic Celery Task.
*   **Frequency**: Every minute (default).
*   **Logic**:
    1.  Fetches all `ConnectorCredentialPair` records.
    2.  For each, checks if `status == ACTIVE`.
    3.  Calculates `next_run = last_successful_index_time + refresh_freq`.
    4.  If `now() >= next_run`:
        *   Creates `IndexAttempt` (State: `NOT_STARTED`).
        *   Calls `try_creating_docfetching_task`.

### 5.2. Isolation & Fetching (`docfetching`)
*   **Proxy Task**: `docfetching_proxy_task` runs in the main Celery pool.
*   **Isolation**: It spawns a **child process** (`docfetching_task`) using `SimpleJobClient`.
    *   This prevents memory leaks or crashes in connector libraries from affecting the main worker.
*   **Execution Flow**:
    1.  **Load Connector**: Instantiates the connector class based on `source`.
    2.  **Fetch**: Calls `load_from_state()` (full) or `load_from_checkpoint()` (incremental).
    3.  **Generator**: The connector yields `Document` objects.
    4.  **Batching**: Documents are collected into batches of `INDEX_BATCH_SIZE` (default 16-500 depending on config).
    5.  **Persistence**: Each batch is serialized and saved to the File Store (MinIO).
    6.  **Dispatch**: For each batch, a `docprocessing_task` is queued.
    7.  **Progress**: `IndexAttempt.total_batches` is updated in Postgres.

### 5.3. Processing Pipeline (`indexing_pipeline.py`)
This is the core transformation logic.

1.  **Filtering**:
    *   Input: List of `Document` objects.
    *   Action: Removes empty docs or those > `MAX_DOCUMENT_CHARS`.
2.  **Metadata Sync**:
    *   Action: Upserts `Document` rows in Postgres.
    *   **Time-Skip**: Checks `doc.doc_updated_at` (source time) vs `db_doc.doc_updated_at`.
    *   Optimization: If source time <= DB time, the doc content is skipped (only metadata updated).
3.  **Image Analysis** (If enabled):
    *   Action: Detects `ImageSection`s.
    *   Call: Sends image to Vision LLM.
    *   Result: Replaces image with generated text description.
4.  **Chunking**:
    *   Class: `Chunker`.
    *   Algorithm: Sentence-aware splitting using a Tokenizer (e.g., Tiktoken/HuggingFace).
    *   Output: `DocAwareChunk`s (Text + Metadata).
5.  **Contextual RAG** (If enabled):
    *   Step A: Generate Document Summary (LLM).
    *   Step B: Generate Chunk Context (LLM). "This chunk describes X in the context of Y".
    *   Result: Prepends context to chunk text for embedding.
6.  **Embedding**:
    *   Class: `IndexingEmbedder`.
    *   Action: Sends text to Model Server.
    *   Output: Dense Vector (e.g., 768 floats).
7.  **Quality Classification**:
    *   Class: `InformationContentClassificationModel`.
    *   Action: Predicts "Usefulness" score (0-1).
    *   Result: Adjusts retrieval boost.
8.  **Vespa Insertion**:
    *   Action: Writes Document + Chunks + Embeddings + ACLs to Vespa.
    *   Mechanism: HTTP/2 Batch Feed.
9.  **Completion**:
    *   Action: Updates `IndexAttempt.completed_batches`.
    *   Finalization: If `completed == total`, marks job `SUCCESS`.

---

## 6. Search & Retrieval Implementation

The search system uses a multi-stage hybrid pipeline.

### 6.1. The Search Tool (`SearchTool`)
Exposed to the Agent as a tool.

1.  **Query Generation** (Parallel):
    *   **Semantic**: LLM rewrites query to be standalone. ("How do I fix it?" -> "Fix server crash").
    *   **Keyword**: LLM extracts keywords. (["server", "crash"]).
2.  **Vespa Retrieval** (Parallel):
    *   Executes queries against Vespa.
    *   **Semantic Query**: Hybrid Search (`hybrid_alpha=0.5`).
    *   **Keyword Query**: Hybrid Search (`hybrid_alpha=0.2`, favors exact match).
3.  **Fusion (RRF)**:
    *   Algorithm: Weighted Reciprocal Rank Fusion.
    *   Logic: Combines ranked lists from all queries. Semantic results get higher weight.
    *   Deduplication: Merges duplicate chunks.
4.  **LLM Refinement** (Deep Research):
    *   **Selection**: LLM selects top relevant chunks from the fused list.
    *   **Expansion**: LLM decides if surrounding chunks are needed.
    *   **Fetch**: Retrieves expanded context from Vespa.
5.  **Formatting**:
    *   Constructs the final context string with citation markers (`[[1]]`).

### 6.2. Low-Level Retrieval (`search_pipeline`)
1.  **Filter Construction**:
    *   **ACLs**: Calls `build_access_filters_for_user`.
    *   Logic: `OR(user_email, group_ids, public)`. Ensures security.
    *   **Metadata**: Applies Time/Source/Tag filters.
2.  **Vespa Query**:
    *   Constructs YQL.
    *   Features: `nearestNeighbor` (Vector), `weakAnd` (Keyword), `rankProfile`.

---

## 7. Chat & Agent Implementation

The Chat logic follows the ReAct pattern.

### 7.1. Session Logic (`process_message`)
1.  **Init**: Creates `ChatMessage` (User) in DB.
2.  **Context**:
    *   Loads Project Files.
    *   Loads Chat History (token limited).
    *   Loads Memories.
3.  **Tool Setup**: Calls `construct_tools` (Search, ImageGen).

### 7.2. The Loop (`run_llm_loop`)
Iterates up to `MAX_LLM_CYCLES` (6).

1.  **Prompt**: Builds System Prompt + History + Tools Schema.
2.  **Invoke**: Calls LLM (LiteLLM).
3.  **Stream**: Emits tokens to frontend.
4.  **Branch**:
    *   **Case A: Answer**: Loop terminates.
    *   **Case B: Tool Call**:
        *   Parses Tool Arguments.
        *   Executes Tool (e.g., `SearchTool.run`).
        *   Appends `TOOL_CALL_RESPONSE` to history.
        *   **Recurse**: Calls LLM again with new history.

### 7.3. Citation Processing
*   **Component**: `DynamicCitationProcessor`.
*   **Input**: Stream of tokens.
*   **Logic**: Detects `[[N]]`. Maps `N` to the `SearchDoc` from the Search Tool response.
*   **Persistence**: Saves citation mapping to Postgres.

---

## 8. API Reference

The backend exposes the following key endpoints via `backend/esa/server/`.

### 8.1. Chat API (`/api/chat/`)
*   `POST /send-message`: Main entry point. Accepts `message`, `session_id`. Streams SSE.
*   `GET /get-chat-session/{id}`: Returns full message history and tool calls.
*   `POST /create-chat-session`: Creates a new empty session.
*   `PUT /rename-chat-session`: Renames session (auto-generated or manual).
*   `DELETE /delete-chat-session/{id}`: Soft deletes a session.
*   `POST /stop-chat-session/{id}`: Sets stop signal in Redis.

### 8.2. Management API (`/api/manage/`)
*   `GET /admin/connector`: Lists all connectors.
*   `POST /admin/connector`: Creates a new connector.
*   `POST /connector/{id}/credential`: Adds credentials to a connector (Creating a CC Pair).
*   `POST /connector/{id}/index`: Triggers manual indexing.
*   `GET /users`: Lists users.
*   `PATCH /users/{id}/promote`: Promotes user to Admin.

### 8.3. Document API (`/api/document/`)
*   `POST /document/search`: Raw search endpoint (for debug/admin).

---

## 9. Infrastructure & Operations

### 9.1. Celery Implementation
*   **Broker**: Redis.
*   **Backend**: Redis.
*   **Task Definition**: `backend/esa/background/celery/tasks/`.
*   **Beat**: Schedules periodic tasks (`check_for_indexing`, `prune_index`).

### 9.2. Vespa Implementation
*   **Schema**: `doc.sd` (Search Definition).
    *   Fields: `content` (index), `title` (index), `embedding` (tensor).
*   **Ranking**: Custom rank profiles.
    *   `hybrid`: `bm25 + vector_score`.
    *   `keyword`: `bm25`.

### 9.3. Security
*   **Encryption**: `Fernet` (symmetric) encryption for Credentials and API Keys in Postgres.
*   **Auth**: JWT (FastAPI Users).
*   **RBAC**: Role-based access control middleware on API routes.
*   **Multi-Tenancy**: `UserTenantMapping` and logic to isolate data per tenant in Postgres and Vespa.
