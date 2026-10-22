# FRIDAY AI Backend Architecture

## 1. System Overview

FRIDAY AI is designed as a **modular monolith** operating on a local-first, privacy-preserving model. It exposes REST and Server-Sent Events (SSE) streaming APIs via FastAPI, backed by an asynchronous SQLite database with SQLite FTS5 for full-text document retrieval.

```
+-----------------------------------------------------------------------+
|                             API LAYER                                 |
|   FastAPI Routers: Health, Conversations, Chat, Projects, Tasks,     |
|   Approvals, Memory, Tools, Git, GitHub, Security, Reports, Voice     |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                         APPLICATION SERVICES                          |
|   - OrchestrationService (Bounded Tool Loop, Context, Verification)   |
|   - ConversationService, ProjectService, RetrievalService (FTS5)     |
|   - TaskService, ApprovalService, SecurityService, SchedulerService  |
+-----------------------------------------------------------------------+
            |                                         |
            v                                         v
+-------------------------+             +-------------------------------+
|      SECURITY LAYER     |             |      INFRASTRUCTURE & TOOLS   |
| - Path Sandbox Checker  |             | - Ollama AI Provider          |
| - Command Policy Engine |             | - Tool Registry & Adapters    |
| - Approval Enforcement  |             | - GitHub Read-Only Client     |
| - Credential Redaction  |             | - Voice Adapters (STT / TTS)  |
| - Audit Event Logger    |             | - SQLAlchemy 2.0 Async / FTS5 |
+-------------------------+             +-------------------------------+
```

## 2. Layered Responsibilities

### A. API Layer (`app/api/`)
- Strict input validation via Pydantic v2 schemas (`app/domain/schemas.py`).
- Centralized exception handlers (`app/api/errors.py`) transforming `FridayException` domain errors into consistent JSON responses.
- Versioned endpoints under `/api/v1/` and standard observability endpoints under `/health/live`, `/health/ready`, and `/api/v1/status`.
- Real-time Server-Sent Events (SSE) streaming in `/api/v1/chat/stream`.

### B. Application Services (`app/services/`)
- **OrchestrationService**: Manages the bounded plan-and-act loop. Injects project context, memories, and RAG document chunks into prompts, executes tools through the `ToolRegistry`, pauses tasks when actions require human approval, and verifies completion using real outputs.
- **RetrievalService**: Traverses approved project roots, filters excluded directories (`.git`, `node_modules`, `.venv`), chunks textual files, hashes content fingerprints, and indexes chunks into SQLite FTS5.
- **TaskService & ApprovalService**: Enforces finite state machines for tasks (`queued -> running -> awaiting_approval -> succeeded / failed / cancelled`) and approvals (`pending -> approved / rejected / expired`).
- **SecurityService**: Performs static code analysis, regex-based secret scanning, and dependency manifest inspection, producing structured reports.

### C. Security Layer (`app/security/`)
- **Path Validation**: Canonicalizes paths using `Path.resolve()`, checks boundaries against registered project directory grants, and blocks directory traversal (`..`) and symlink escapes.
- **Command Policy**: Whitelists safe commands (`git`, `pytest`, `ruff`), strictly rejects dangerous binaries (`sudo`, `rm`, `mkfs`), and disallows shell metacharacters (`|`, `&`, `;`, `$`, `` ` ``).
- **Credential Redaction**: Recursively masks API keys, bearer tokens, private keys, and secrets in logs and diagnostic outputs.
- **Audit Logging**: Persists tamper-evident security records into the `audit_events` table.

### D. AI Providers (`app/providers/`)
- **OllamaProvider**: Direct asynchronous HTTP client to local Ollama (`/api/chat`, `/api/tags`). Supports streaming deltas and capability checks.
- **CloudAIProviderAdapter**: Disabled by default. Requires explicit user opt-in (`CLOUD_AI_ENABLED=true`) before connecting to external cloud endpoints.
- **MockAIProvider**: Deterministic mock provider for reproducible unit and integration tests without network dependencies.

## 3. Database Relationships

The database is built on SQLAlchemy 2.0 with asynchronous SQLite (`aiosqlite`) configured with WAL mode and `PRAGMA foreign_keys = ON`.

Key entities:
- **Conversation** `1:N` **Message** (Cascading deletion)
- **Project** `1:N` **ProjectDirectoryGrant** (Authorized filesystem roots)
- **Project** `1:N` **DocumentIndex** `1:N` **DocumentChunk** (Content chunks mapped to FTS5)
- **Project** `1:N` **MemoryRecord** (Scoped memories with categories)
- **Task** `1:N` **TaskEvent**, **ApprovalRequest**, **ToolExecutionRecord**
- **SecurityReport** `1:N` **SecurityFinding**
- **ScheduledJob** `1:N` **JobExecutionHistory**
