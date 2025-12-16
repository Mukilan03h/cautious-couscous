# ESA Technical Architecture Deep Dive

This documentation provides an exhaustive technical specification of the ESA (formerly Onyx/Danswer) platform. It details the internal mechanisms, data structures, algorithms, and logic flows of the system without including raw source code.

---

## 1. System Architecture Overview

ESA is an enterprise-grade Gen-AI and Search platform designed for modularity, scalability, and security. It follows a microservices-like architecture orchestrated via Docker or Kubernetes.

### 1.1. Core Components

*   **Frontend Application (`web/`)**
    *   **Framework**: Next.js 15+ (App Router).
    *   **Language**: TypeScript, React 18.
    *   **Styling**: Tailwind CSS.
    *   **State Management**: SWR for data fetching, React Context for local state.
    *   **Responsibilities**: Rendering the Chat UI, Admin Dashboard, and User Settings. It communicates exclusively with the Backend API.

*   **Backend API Server (`backend/esa/server/`)**
    *   **Framework**: FastAPI (Python 3.11+).
    *   **Concurrency**: Uvicorn (ASGI) with async/await.
    *   **Responsibilities**:
        *   Exposing REST endpoints for Chat, Search, Management, and Auth.
        *   Handling authentication and session management.
        *   Orchestrating the Agentic Chat Loop (`run_llm_loop`).
        *   Interfacing with the Database and Vector Store.

*   **Background Workers (Celery)**
    *   **Framework**: Celery with Redis broker.
    *   **Executor**: Pool based (Threads vs Processes depends on task type).
    *   **Worker Types**:
        *   `primary`: Handles lightweight orchestration, signal checking, and maintenance.
        *   `docfetching`: Dedicated to I/O intensive connector tasks (fetching data from APIs). Runs isolated processes.
        *   `docprocessing`: Dedicated to CPU/GPU intensive tasks (Chunking, Embedding).
        *   `light`: Ultra-fast tasks like permission syncing or metadata updates.
        *   `heavy`: Long-running maintenance like index pruning.

*   **Relational Database (PostgreSQL)**
    *   **ORM**: SQLAlchemy (Async and Sync sessions).
    *   **Migrations**: Alembic.
    *   **Role**: Source of truth for Users, Permissions, Connectors, Chat History, and Indexing State.

*   **Vector Database (Vespa)**
    *   **Role**: Stores document vectors (embeddings) and metadata for retrieval.
    *   **Capabilities**: Hybrid Search (BM25 + ANN), Tensor Ranking, Grouping/Aggregation.
    *   **Schema**: customized schema defining fields like `content`, `title`, `embedding`, `access_control_list`.

*   **Cache & Message Broker (Redis)**
    *   **Role**:
        *   Celery Task Queue.
        *   Distributed Locking (e.g., ensuring only one indexing job runs per connector).
        *   Pub/Sub for Real-time Stop Signals (stopping a stream generation).
        *   Caching frequently accessed configuration.

*   **Object Storage (MinIO / S3)**
    *   **Role**: Stores intermediate document batches during ingestion, user uploaded files, and connector state checkpoints.

*   **Model Server**
    *   **Role**: Dedicated service for running local Inference (Bi-Encoders for embedding, Cross-Encoders for reranking).
    *   **Protocol**: HTTP/gRPC.

---

## 2. Data Model Specification

The database schema is the backbone of the system. Below is a detailed breakdown of the key entities.

### 2.1. Authentication & User Management

*   **`user` Table**
    *   `id` (UUID): Primary Key.
    *   `email` (String): User's email address.
    *   `role` (Enum): `BASIC`, `ADMIN`, `CURATOR`. Controls access to admin endpoints.
    *   `preferences` (JSONB): UI settings like theme, auto-scroll.
    *   `is_active` (Boolean): Soft deletion flag.

*   **`oauth_account` Table**
    *   `id` (UUID): PK.
    *   `user_id` (FK): Links to `user`.
    *   `provider` (String): e.g., "google", "github", "oidc".
    *   `access_token`, `refresh_token` (Text): Stored tokens for the IDP session.

*   **`user_tenant_mapping` Table** (Multi-tenant)
    *   `user_id`, `tenant_id`: Composite PK mapping a user to a logical tenant.

### 2.2. Connectors & Ingestion Config

*   **`connector` Table**
    *   `id` (Int): PK.
    *   `source` (Enum): Type of data source (e.g., `GOOGLE_DRIVE`, `SLACK`, `WEB`).
    *   `connector_specific_config` (JSONB): Arbitrary config (e.g., "shared_drive_ids" for GDrive).
    *   `refresh_freq` (Int): Seconds between indexing runs.
    *   `prune_freq` (Int): Seconds between prune runs (detecting deleted docs).

*   **`credential` Table**
    *   `id` (Int): PK.
    *   `credential_json` (Encrypted JSON): Stores sensitive keys/tokens.
    *   `admin_public` (Boolean): If true, usable by all admins.

*   **`connector_credential_pair` Table** ("CC Pair")
    *   **Concept**: This is the atomic unit of indexing. A Connector (what to index) + Credential (how to access it).
    *   `connector_id`, `credential_id`: FKs.
    *   `status` (Enum): `ACTIVE`, `PAUSED`, `DELETING`.
    *   `last_successful_index_time` (DateTime): High watermark for incremental syncs.
    *   `access_type` (Enum): `PUBLIC`, `PRIVATE`. Controls default visibility of indexed docs.

### 2.3. Indexing State

*   **`index_attempt` Table**
    *   **Concept**: Represents a single "Job" to index data from a CC Pair.
    *   `id` (Int): PK.
    *   `status` (Enum): `NOT_STARTED`, `IN_PROGRESS`, `SUCCESS`, `FAILED`, `PARTIAL_SUCCESS`.
    *   `total_batches` (Int): Number of document batches generated by the fetch step.
    *   `completed_batches` (Int): Number of batches processed by the processing step.
    *   `new_docs_indexed` (Int): Counter.
    *   `error_msg` (Text): Summary failure reason.
    *   `full_exception_trace` (Text): Stack trace if failed.

*   **`document` Table**
    *   **Concept**: Tracks the existence and metadata of a document in Postgres (source of truth vs Vespa).
    *   `id` (String): URL or unique ID from source.
    *   `semantic_id` (String): Title or human-readable name.
    *   `doc_updated_at` (DateTime): Last modification time reported by the source. Used for "Time-Skip" optimization.
    *   `access_control_list` (Array): List of user emails/groups who can view this.
    *   `boost` (Int): Manual relevance boost.

### 2.4. Chat History & Personas

*   **`persona` Table** ("Assistant")
    *   `id` (Int): PK.
    *   `system_prompt` (Text): The base instructions for the LLM.
    *   `tools` (M2M): Relation to enabled tools.
    *   `document_sets` (M2M): Relation to allowed document sets.
    *   `retrieval_options` (JSON): Configuration for search (e.g., `num_chunks`, `recency_bias`).

*   **`chat_session` Table**
    *   `id` (UUID): PK.
    *   `user_id` (FK): Owner.
    *   `persona_id` (FK): The assistant used.
    *   `description` (Text): Auto-generated title.

*   **`chat_message` Table**
    *   `id` (Int): PK.
    *   `chat_session_id` (FK).
    *   `message_type` (Enum): `USER`, `ASSISTANT`, `SYSTEM`, `TOOL_CALL`, `TOOL_CALL_RESPONSE`.
    *   `message` (Text): The content.
    *   `tool_calls` (JSON): Metadata about tool execution.
    *   `citations` (JSON): Mapping of citation indices (e.g., "1") to `SearchDoc` IDs.

---

## 3. Ingestion Pipeline Subsystem

The Ingestion Pipeline is a complex, distributed system responsible for "Extract, Transform, Load" (ETL) of documents.

### 3.1. Orchestration Layer
*   **Trigger**: `check_for_indexing` (Celery Beat task).
*   **Logic**:
    1.  Iterates all `ConnectorCredentialPair`s.
    2.  Checks `last_successful_index_time` vs `refresh_freq`.
    3.  If due, creates an `IndexAttempt` (Status: `NOT_STARTED`).
    4.  Calls `try_creating_docfetching_task`.

### 3.2. DocFetching Layer (Extract)
*   **Task**: `docfetching_proxy_task` -> `docfetching_task`.
*   **Mechanism**: Uses `SimpleJobClient` to spawn a **separate OS process**.
    *   *Why?* Connectors use various third-party libraries (Google Client, Slack Client) which may leak memory or segfault. Isolation protects the main worker.
*   **Execution**:
    1.  Instantiates the specific Connector class (e.g., `GoogleDriveConnector`).
    2.  Calls `load_from_checkpoint` (incremental) or `load_from_state` (full).
    3.  **Generator**: The connector yields `Document` objects.
    4.  **Batching**: The task accumulates documents into batches (default 500).
    5.  **Persistence**: Batches are serialized (Pickle/JSON) and uploaded to FileStore (MinIO).
    6.  **Handoff**: For every batch, a `docprocessing_task` is triggered in Celery.

### 3.3. DocProcessing Layer (Transform & Load)
*   **Task**: `docprocessing_task`.
*   **Input**: Batch ID.
*   **Process**: Runs `run_indexing_pipeline`.

#### Detailed Pipeline Steps:
1.  **Filter Phase**:
    *   Checks `Document.title` and `Document.sections`.
    *   Discards empty documents or those exceeding `MAX_DOCUMENT_CHARS`.
2.  **DB Sync Phase**:
    *   Fetches existing `Document` rows from Postgres for the batch IDs.
    *   **Time-Skip**: Compares incoming `doc_updated_at` with DB `doc_updated_at`.
    *   If incoming is older or equal, the doc is marked "Already Updated" and skipped (saving GPU cycles).
    *   Upserts metadata (ACLs, Titles) to Postgres.
3.  **Image Analysis Phase**:
    *   Scans for `ImageSection`s.
    *   If enabled, calls a Vision LLM to describe the image.
    *   Replaces the image with the textual description for indexing.
4.  **Chunking Phase**:
    *   Class: `Chunker`.
    *   Logic: Splits text into `DocAwareChunk` objects.
    *   Strategy: Uses a tokenizer (e.g., BERT/GPT) to ensure chunks fit within embedding model limits (e.g., 512 tokens).
    *   Maintains "Window" overlap.
5.  **Contextual RAG Phase** (Advanced):
    *   If enabled, sends the *entire document* (or a summary) to an LLM.
    *   Prompt: "Describe this chunk's meaning within the context of the document."
    *   The generated context is prepended to the chunk text.
6.  **Embedding Phase**:
    *   Class: `IndexingEmbedder`.
    *   Action: Sends chunk text to the Model Server.
    *   Output: Dense Vector (e.g., 768 dimensions).
7.  **Classification Phase**:
    *   Class: `InformationContentClassificationModel`.
    *   Action: Scores the chunk (0.0 to 1.0) on how "informative" it is.
    *   Result: Used to boost/penalize the chunk score in Vespa.
8.  **Vespa Write Phase**:
    *   Class: `VespaIndex`.
    *   Action: Pushes Chunks + Embeddings + ACLs to Vespa via HTTP/2 (HTTPX).
    *   Uses a "Backoff" retry strategy for stability.

### 3.4. Coordination & Consistency
*   **Class**: `IndexingCoordination`.
*   **Mechanism**:
    *   The `docfetching` task updates `total_batches` in `IndexAttempt`.
    *   Each `docprocessing` task atomically increments `completed_batches`.
    *   When `completed_batches == total_batches`, the `IndexAttempt` is marked `SUCCESS`.
    *   **Stall Detection**: If `last_progress_time` is > 3 hours ago, the job is marked `FAILED`.

---

## 4. Search & Retrieval Subsystem

The search subsystem is a sophisticated pipeline involving query understanding, hybrid retrieval, and re-ranking.

### 4.1. The Search Tool (`SearchTool`)
This component is exposed to the LLM as a tool ("internal_search").

#### 4.1.1. Query Generation Strategy
The tool does not just run the user's raw query. It uses an LLM to generate optimal queries:
1.  **Semantic Rephrasing**: "Rewrite the user's query to be a standalone search query, resolving coreferences."
    *   *Input*: "How do I fix it?" (Context: Server crashed).
    *   *Output*: "Server crash fix procedure".
2.  **Keyword Expansion**: "List 3-5 keywords related to this topic."
    *   *Output*: ["server", "crash", "logs", "restart"].

#### 4.1.2. Parallel Search Execution
The system executes multiple searches against Vespa concurrently using `run_functions_tuples_in_parallel`.
*   **Semantic Queries**: Run with `hybrid_alpha=0.5` (Balanced Vector + Keyword).
*   **Keyword Queries**: Run with `hybrid_alpha=0.2` (Keyword Heavy).
*   **Original Query**: Run as a fallback.

#### 4.1.3. Reciprocal Rank Fusion (RRF)
The results from the parallel searches are merged using Weighted RRF.
*   **Formula**: `Score = sum(Weight * (1 / (k + Rank)))`.
*   **Weights**: Semantic queries get higher weight than keyword queries.
*   **Deduplication**: Identical chunks found by multiple queries have their scores boosted.

#### 4.1.4. LLM Selection & Expansion (Deep Research)
1.  **Selection**: The top K chunks (e.g., 50) are presented to a fast LLM.
    *   *Prompt*: "Select the chunks that directly help answer the user's question."
2.  **Expansion**: For the selected chunks, the system checks if they are "cut off".
    *   If yes, the system fetches the *surrounding* chunks from Vespa (chunk index -1 and +1).
3.  **Merge**: Overlapping expanded sections are stitched together into coherent `InferenceSection`s.

### 4.2. The Search Pipeline (`search_pipeline`)
This is the lower-level function calling Vespa.

#### 4.2.1. Filter Construction
*   **ACL Filters**: `build_access_filters_for_user`.
    *   Fetches the user's email and groups.
    *   Constructs a Vespa filter: `OR(user_email, group_1, group_2, public)`.
*   **Source Filters**: "Only search Slack".
*   **Time Filters**: "Only docs from last week".

#### 4.2.2. Vespa Query Construction
*   Constructs a YQL (Vespa Query Language) string.
*   Combines the `nearestNeighbor` operator (Vector Search) with `weakAnd` (Keyword Search).
*   Applies the filters.
*   Requests specific summaries/fields.

---

## 5. Chat & Agent Subsystem

The Chat system implements a ReAct (Reasoning + Acting) loop, allowing the LLM to use tools.

### 5.1. Initialization (`process_message`)
1.  **Validation**: Checks API limits, User permissions.
2.  **Session Creation**: Creates `ChatMessage` (User) in Postgres.
3.  **Context Loading**:
    *   Loads Project files (if any).
    *   Loads recent Chat History (Token limited).
    *   Loads User Memories.
4.  **Tool Construction**: Calls `construct_tools` to instantiate available tools (`SearchTool`, `ImageGenerationTool`) based on the Persona configuration.

### 5.2. The LLM Loop (`run_llm_loop`)
This function drives the conversation.

*   **Max Cycles**: Hardcoded to 6 (prevent infinite loops).
*   **Cycle Steps**:
    1.  **Prompt Building**: `build_system_prompt` + History + Tool Definitions.
    2.  **Inference**: Calls `LLM.invoke` (LiteLLM).
    3.  **Streaming**: Emits `Packet`s (tokens, tool calls) to the frontend via `Emitter`.
    4.  **Decision**:
        *   If **Content**: The loop ends.
        *   If **Tool Call**:
            *   Parses arguments (JSON).
            *   Executes `Tool.run()`.
            *   Appends `TOOL_CALL_RESPONSE` to history.
            *   **Continues** to next cycle.

### 5.3. Citation Handling
*   **Processor**: `DynamicCitationProcessor`.
*   **Logic**:
    *   The Search Tool returns `SearchDoc` objects with IDs.
    *   The LLM is prompted to use `[[citation_id]]` format.
    *   The Processor parses the output stream.
    *   When `[[1]]` is detected, it maps it to the actual Document metadata.
    *   Saves the mapping in `ChatMessage.citations`.

---

## 6. API Reference (Backend)

The API is structured using FastAPI Routers.

### 6.1. Chat Router (`/chat`)
*   `POST /send-message`: Main entry point for chat. Streams response.
*   `GET /get-chat-session/{id}`: Retrieves full history.
*   `POST /create-chat-session`: Starts a new thread.
*   `PUT /rename-chat-session`: Renames a thread (optionally using LLM generation).

### 6.2. Management Routers
*   `/manage/admin`: User management, Connector management.
*   `/manage/users`: Current user profile.

### 6.3. Indexing Router
*   `/manage/connector/{id}/index`: Triggers an immediate index run.

---

## 7. Infrastructure Details

### 7.1. Celery Configuration
*   **Broker**: Redis (`redis-stack` image).
*   **Result Backend**: Redis.
*   **Queues**:
    *   `celery` (default): Mixed tasks.
    *   `vespa_metadata_sync`: High priority updates.
    *   `connector_pruning`: Low priority, long running.

### 7.2. Vespa Configuration
*   **Application Package**: Defines the schema (`doc.sd`).
*   **Document Definition**:
    *   `field content`: String, Index, Summary.
    *   `field embedding`: Tensor<float>(x[768]).
    *   `field access_control_list`: Array<String>, Attribute, FastSearch.
*   **Rank Profiles**: Define how scores are calculated (e.g., `bm25 + 10 * closeness(embedding)`).

### 7.3. Security Implementation
*   **Encryption**: `Connector` credentials are encrypted at rest in Postgres using `Fernet` (symmetric encryption).
*   **Tokens**: API uses JWT (FastAPI Users).
*   **CSRF**: Protection enabled for state-changing endpoints.
*   **RBAC**:
    *   **Admins**: Can manage all connectors/users.
    *   **Curators**: Can manage document sets but not system config.
    *   **Basic**: Can only chat and manage own chats.

### 7.4. Multi-Tenancy (Enterprise)
*   **Schema**: Uses a shared-schema approach where possible, or schema-per-tenant.
*   **Isolation**: `UserTenantMapping` enforces tenant boundaries.
*   **Middleware**: `TenantMiddleware` extracts tenant ID from headers/domains and sets the context for DB queries.
