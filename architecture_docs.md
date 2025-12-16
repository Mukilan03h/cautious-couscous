# ESA Technical Architecture Documentation

This document provides a comprehensive technical overview of the ESA (formerly Onyx/Danswer) architecture, detailing the implementation of its core components, pipelines, and data models. It is intended for engineers and architects seeking to understand the internal mechanisms of the system.

## 1. System Overview

ESA is a Gen-AI and Enterprise Search platform designed to connect to various data sources, index them, and provide an intelligent chat interface. The system is built on a modular architecture comprising the following key components:

*   **Frontend**: Built with **Next.js** (App Router), React, and Tailwind CSS. It handles the user interface for chat, admin settings, and visualizations.
*   **Backend**: A **Python** application using **FastAPI** for the REST API and **Celery** for asynchronous background processing.
*   **Database**: **PostgreSQL** serves as the primary source of truth for relational data (users, connectors, chat history).
*   **Vector Search Engine**: **Vespa** is used for storing document vectors and metadata, enabling hybrid search (keyword + semantic).
*   **Caching & Broker**: **Redis** is used for caching, as a message broker for Celery, and for inter-process communication (locking, stop signals).
*   **Object Storage**: **MinIO** (or S3-compatible storage) is used for storing file uploads and intermediate document batches.
*   **Model Server**: A dedicated service (often running Triton or a custom Python server) for running embedding and reranking models.

## 2. Core Data Models (Postgres)

The relational database schema is defined using SQLAlchemy. Key entities include:

### 2.1. Authentication & Users
*   **User**: Represents a system user. Includes preferences, roles (Admin, Basic), and relationships to authentication methods.
*   **OAuthAccount**: Links users to external identity providers (Google, GitHub, OIDC, SAML).
*   **UserTenantMapping**: In multi-tenant deployments, maps users to specific tenants.
*   **UserGroup**: Groups users for permission management (Enterprise Edition).

### 2.2. Connectors & Ingestion
*   **Connector**: Defines a data source type (e.g., Google Drive, Slack, Web). Contains configuration frequencies (refresh, prune).
*   **Credential**: Stores encrypted credentials (API keys, tokens) for accessing data sources.
*   **ConnectorCredentialPair (CC Pair)**: The binding between a Connector and a Credential. This is the unit of execution for indexing jobs.
    *   Tracks status (`ACTIVE`, `PAUSED`, `FAILING`).
    *   Tracks indexing progress (`last_successful_index_time`, `total_docs_indexed`).
*   **IndexAttempt**: Represents a specific run of an indexing job.
    *   Tracks status (`IN_PROGRESS`, `SUCCESS`, `FAILED`).
    *   Links to `SearchSettings` (embedding model used).
    *   Stores progress metrics (batches completed, docs indexed).

### 2.3. Documents
*   **Document**: Stores metadata about indexed documents in Postgres.
    *   `id`: Unique identifier (URL or internal ID).
    *   `semantic_id`: Human-readable identifier (Title).
    *   `boost`: Manual boost score.
    *   `access_control_list` / `external_user_emails`: Permissions synced from the source.
    *   `doc_updated_at`: Timestamp from the source system to detect changes.
*   **ChunkStats**: Stores statistics about individual document chunks (e.g., information density boosts).

### 2.4. Chat & Agents
*   **ChatSession**: Represents a conversation thread.
    *   Links to a `Persona` (Assistant) and `User`.
*   **ChatMessage**: A message within a session.
    *   `message_type`: `USER`, `ASSISTANT`, `SYSTEM`, `TOOL_CALL`, `TOOL_CALL_RESPONSE`.
    *   `tool_calls`: Relationships to tool executions.
    *   `citations`: Links to `SearchDoc`s used for the answer.
*   **Persona**: Defines an AI Assistant.
    *   `system_prompt`: Custom instructions.
    *   `tools`: List of enabled tools.
    *   `document_sets`: Restricted knowledge base.
*   **ToolCall**: Records the input arguments and output response of a tool execution for history and replay.

## 3. Ingestion Pipeline (The "Write" Path)

The ingestion pipeline is responsible for fetching data from external sources, processing it, and indexing it into Vespa. It is designed for high throughput, fault tolerance, and isolation.

### 3.1. Scheduling & Triggering
*   **`check_for_indexing`**: A periodic Celery beat task that scans `ConnectorCredentialPair`s.
*   It determines if a connector needs to run based on its schedule (`refresh_freq`).
*   It creates an `IndexAttempt` entry in Postgres and spawns a `docfetching` task.

### 3.2. Architecture: Process Isolation
To prevent unstable connectors from crashing the main worker, the system uses a multi-process architecture:
1.  **Proxy Task**: `docfetching_proxy_task` runs on the main worker.
2.  **Job Client**: Uses `SimpleJobClient` to spawn a completely new OS process (`docfetching_task`) for the actual work.
3.  **Watchdog**: The proxy task monitors the spawned process, handling timeouts and updating the `IndexAttempt` status.

### 3.3. Phase 1: Document Fetching (`docfetching`)
*   Runs the connector-specific code (e.g., using Google Drive API).
*   Fetches documents and converts them to the internal `Document` model.
*   **Batching**: Documents are accumulated into batches (e.g., 500 docs).
*   **Storage**: Batches are serialized and saved to the FileStore (MinIO/S3).
*   **Handoff**: For each saved batch, a `docprocessing_task` is spawned in Celery.

### 3.4. Phase 2: Document Processing (`docprocessing`)
This task consumes a batch from the FileStore and runs it through the `indexing_pipeline`.

#### The Indexing Pipeline Steps:
1.  **Filtering**:
    *   Removes empty documents.
    *   Removes documents exceeding character limits.
2.  **Metadata Synchronization**:
    *   Upserts `Document` rows in Postgres.
    *   **Time-Skip Optimization**: Checks `doc_updated_at`. If the local version is newer or equal to the source, the document processing is skipped (only metadata is updated).
3.  **Image Processing**:
    *   Identifies `ImageSection`s in the document.
    *   Uses a Vision LLM (e.g., GPT-4o) to generate a text summary of the image.
    *   Replaces/Augments the image section with the text summary.
4.  **Chunking**:
    *   Splits document text into `DocAwareChunk`s using a tokenizer-aware splitter.
    *   Respects sentence and paragraph boundaries.
5.  **Contextual RAG (Optional & Advanced)**:
    *   If enabled, uses an LLM to generate:
        *   **Document Summary**: A concise summary of the whole document.
        *   **Chunk Context**: A localized summary explaining "what this chunk is about" in relation to the document.
    *   This context is prepended to the chunk text for embedding, improving retrieval accuracy for decontextualized chunks.
6.  **Embedding**:
    *   Sends chunk text (and context) to the Model Server.
    *   Generates dense vectors (embeddings).
7.  **Content Classification**:
    *   Uses a specialized small model (`InformationContentClassificationModel`) to score chunks based on their information density.
    *   Assigns a "boost factor" to helpful chunks and penalizes "fluff".
8.  **Vespa Insertion**:
    *   Writes chunks, embeddings, and metadata to Vespa.
    *   Uses a `AccessAwareChunk` wrapper to attach permission tags (ACLs) to the Vespa document.
9.  **Post-Processing**:
    *   Updates `IndexAttempt` progress in Postgres via `IndexingCoordination`.
    *   Handles failures (recording `IndexAttemptError`).

### 3.5. Coordination
`IndexingCoordination` uses Postgres to atomically track the state of an indexing attempt:
*   Counts `total_batches` vs `completed_batches`.
*   Detects stalls (if no progress is made for hours).
*   Marks the attempt as `SUCCESS` or `PARTIAL_SUCCESS` when all batches are done.

## 4. Search & Retrieval (The "Read" Path)

The search system employs a sophisticated hybrid pipeline involving Query Expansion, Parallel Search, and LLM Refinement.

### 4.1. The Search Tool (`SearchTool`)
This is the primary interface for the Agent to access knowledge.

#### Step 1: Query Generation
The system uses an LLM to generate optimized queries based on the user's chat message and history.
*   **Semantic Rephrasing**: Rewrites the query to be more search-friendly (resolving coreferences, removing conversational filler).
*   **Keyword Expansion**: Generates a list of specific keywords related to the query.

#### Step 2: Parallel Execution
The system executes multiple searches against Vespa in parallel:
*   **Semantic Queries**: Run with a standard `hybrid_alpha` (balancing dense vector and sparse keyword scores).
*   **Keyword Queries**: Run with a low `hybrid_alpha` (favoring keyword matching).
*   **Original Query**: Also executed to preserve the user's original intent.

#### Step 3: Fusion (RRF)
Results from all parallel searches are combined using **Weighted Reciprocal Rank Fusion (RRF)**.
*   Results are weighted based on their source (Semantic vs. Keyword).
*   Duplicate chunks are merged.

#### Step 4: LLM Selection & Refinement
To reduce noise and context window usage:
1.  **Trimming**: Sections are trimmed to fit a "Selection" token budget.
2.  **Selection**: An LLM is presented with the retrieved sections and asked to **select** only the most relevant ones.
3.  **Expansion**: For the selected sections, the LLM is asked if it needs more surrounding context (chunks before/after).
    *   If yes, the system fetches adjacent chunks from Vespa.
4.  **Merging**: Overlapping expanded sections are merged into coherent passages.

#### Step 5: Response
The final text passages are returned to the main Chat Loop, along with citation metadata.

### 4.2. The Search Pipeline
Underlying the tool is the low-level `search_pipeline` which interfaces with Vespa.
*   **Filtering**: Builds `IndexFilters`.
    *   **ACLs**: Applies `build_access_filters_for_user` to ensure users only see docs they have access to.
    *   **Time/Source**: Applies filters extracted from the query (e.g., "emails from last week").
*   **Vespa Query**: Constructs the YQL (Vespa Query Language) request including embeddings and filters.

## 5. Chat & Agent Loop

The core intelligence resides in the `run_llm_loop` function, which implements a ReAct (Reasoning + Acting) loop.

### 5.1. Context Construction
Before calling the LLM, the system constructs the context window:
*   **System Prompt**: Defines the Persona's behavior and capabilities.
*   **Chat History**: Loads recent messages (`create_chat_history_chain`).
*   **Project Context**: Loads active project files (`extract_project_file_texts_and_images`).
*   **Memories**: Injects relevant user memories.
*   **Reminders**: Adds dynamic reminders (e.g., "You just ran a search, remember to cite sources").

### 5.2. The Agent Loop
The loop runs for a maximum of `MAX_LLM_CYCLES` (default 6).

1.  **Think**: The LLM generates a response, potentially including "Reasoning" (Chain of Thought).
2.  **Tool Selection**: The LLM may decide to call a tool (e.g., `Internal Search`, `Image Generation`).
3.  **Act**: The system executes the requested tool(s).
    *   **Streaming**: Tool inputs and outputs are streamed to the frontend via `Emitter` packets.
    *   **Parallelism**: If multiple tools are called, they can be executed in parallel (where supported).
4.  **Observe**: The tool output is added to the chat history as a `TOOL_CALL_RESPONSE` message.
5.  **Loop**: The process repeats with the new history.

### 5.3. Citation Processing
*   The `DynamicCitationProcessor` monitors the generation.
*   It maps citation markers (e.g., `[[1]]`) in the LLM output to actual `SearchDoc` objects retrieved by the Search Tool.
*   This ensures that citations are accurate and clickable in the UI.

## 6. Infrastructure & Deployment

### 6.1. Celery Workers
The background processing is split into specialized worker queues to optimize resource usage:
*   **`docfetching`**: Network-bound. Handles connector APIs.
*   **`docprocessing`**: CPU/Memory-bound. Handles embedding and indexing.
*   **`primary`**: General management and orchestration.
*   **`light`**: High-frequency, low-latency tasks (e.g., permission syncing, Vespa updates).
*   **`heavy`**: Long-running maintenance tasks (e.g., pruning).

### 6.2. Vespa (Vector Database)
*   Used for storing embeddings and metadata.
*   Supports **Hybrid Search**: Combines BM25 (keyword) and ANN (Approximate Nearest Neighbor) vector search.
*   **Tensor Operations**: Performs re-ranking and score adjustment directly in the query engine.

### 6.3. Permissions & Security
*   **ACLs**: Permissions are synced from source systems (e.g., Google Drive permissions).
*   **Groups**: Users can be mapped to groups.
*   **Query Time Enforcement**: Filters are applied at the Vespa query level, ensuring unauthorized documents are never returned to the application layer.
