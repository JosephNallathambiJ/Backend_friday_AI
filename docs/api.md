# FRIDAY AI API Reference

The backend exposes RESTful HTTP and Server-Sent Events (SSE) endpoints. All requests and responses are typed via Pydantic v2. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc`.

## Base URLs
- Local Default: `http://127.0.0.1:8000`

---

## 1. Observability & Health

### `GET /health/live`
Indicates whether the process is alive.
- **Response**: `200 OK`
```json
{
  "status": "alive"
}
```

### `GET /health/ready`
Checks database connectivity and readiness.
- **Response**: `200 OK`
```json
{
  "status": "ready",
  "database": "connected"
}
```

### `GET /api/v1/status`
Reports core system status, active database connection, Ollama availability, and installed models.
- **Response**: `200 OK`
```json
{
  "success": true,
  "data": {
    "app_name": "friday-ai-backend",
    "version": "0.1.0",
    "environment": "development",
    "database_connected": true,
    "ollama_connected": true,
    "default_model": "gemma4:12b",
    "cloud_ai_enabled": false,
    "scheduler_enabled": true
  }
}
```

---

## 2. Conversations & Chat

### `POST /api/v1/conversations`
Create a new conversation session.
- **Request Body**:
```json
{
  "title": "Project Refactoring",
  "project_id": "optional-uuid"
}
```
- **Response**: `201 Created`

### `GET /api/v1/conversations`
List conversations with pagination (`skip`, `limit`).

### `GET /api/v1/conversations/{conversation_id}`
Retrieve conversation details and associated messages.

### `PATCH /api/v1/conversations/{conversation_id}`
Rename a conversation.

### `DELETE /api/v1/conversations/{conversation_id}`
Delete a conversation and all cascading message records.

### `POST /api/v1/chat`
Execute a non-streaming AI chat turn through the orchestration engine.
- **Request Body**:
```json
{
  "conversation_id": "uuid",
  "message": "What is the structure of this project?",
  "project_id": "optional-uuid"
}
```
- **Response**: `200 OK`
```json
{
  "success": true,
  "data": {
    "message_id": "uuid",
    "role": "assistant",
    "content": "The project follows a modular monolithic architecture...",
    "tool_calls": []
  }
}
```

### `POST /api/v1/chat/stream`
Stream assistant response tokens and execution events via Server-Sent Events (`text/event-stream`).
- **SSE Events Emitted**:
  - `message_start`: Metadata and request ID.
  - `text_delta`: Incremental token deltas `{"delta": "..."}`.
  - `tool_proposed`: Emitted when the model proposes an action.
  - `approval_required`: Emitted when an action requires human approval.
  - `message_completed`: Generation finished with full persisted message.
  - `error`: Error payload on unexpected failures.

---

## 3. Projects & RAG Document Search

### `POST /api/v1/projects`
Register a project workspace.
```json
{
  "name": "BackendProject",
  "description": "FRIDAY AI workspace",
  "root_path": "/Users/dsceimaclab03/Downloads/DB-FRIDAY"
}
```

### `POST /api/v1/projects/{project_id}/index`
Trigger file discovery, text chunking, and SQLite FTS5 full-text indexing for an approved project root.

### `GET /api/v1/projects/{project_id}/search?query=security`
Perform full-text search across indexed project documents using FTS5 BM25 ranking.

---

## 4. Tasks & Approval Workflow

### `GET /api/v1/tasks`
List all tasks and their state machine statuses (`queued`, `running`, `awaiting_approval`, `succeeded`, `failed`, `cancelled`).

### `POST /api/v1/tasks/{task_id}/cancel`
Cancel an active task.

### `GET /api/v1/approvals`
List pending human approval requests for elevated actions.

### `POST /api/v1/approvals/{approval_id}/decision`
Submit an approval or rejection decision.
- **Request Body**:
```json
{
  "status": "approved",
  "reason": "Authorized execution of git status"
}
```

---

## 5. Security Analysis & Reports

### `POST /api/v1/security/scan`
Scan an authorized project root for hardcoded secrets, security vulnerabilities, and configuration flaws.
- **Request Body**:
```json
{
  "project_id": "uuid"
}
```
- **Response**: `200 OK` returns generated findings with severity and remediation suggestions.

### `GET /api/v1/reports/{report_id}?format=markdown`
Retrieve a security report in JSON or formatted Markdown.
