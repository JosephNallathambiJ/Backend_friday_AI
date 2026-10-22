# FRIDAY AI — Tactical HUD Frontend-to-Backend API Contract

This document provides the complete API and real-time specifications for the separate frontend developer building the **FRIDAY AI Futuristic Tactical HUD Interface** (Systems Online telemetry, Circular Visualizer, Voice Command stream, Controlled Terminal Panel, Quick Actions, and Settings).

---

## 1. Base URL & Networking Architecture

- **Local Development REST Base URL**: `http://127.0.0.1:8000/api/v1`
- **Health / Readiness URL**: `http://127.0.0.1:8000/health` (or `/api/v1/health`)
- **Real-Time WebSocket URL**: `ws://127.0.0.1:8000/api/v1/events`
- **Interactive OpenAPI Documentation**: `http://127.0.0.1:8000/docs`
- **Default Network Binding**: Local loopback interface (`127.0.0.1`).
- **CORS Allowed Origins**:
  - `http://localhost:3000`, `http://localhost:5173`
  - `http://127.0.0.1:3000`, `http://127.0.0.1:5173`
  - `http://tauri.localhost`

---

## 2. Authentication & Authorization

All API endpoints accept an optional or required API key depending on `API_KEY` configuration in `.env`.
- **HTTP Header**: `X-API-Key: <secret_key>`
- **WebSocket Query Param**: `ws://127.0.0.1:8000/api/v1/events?token=<secret_key>&user_id=<user_id>`
- When running locally without `API_KEY` set, requests default to authenticated user `"local_user"`.

---

## 3. Standard Response & Error Envelope

All responses are wrapped in a typed JSON envelope:

### Success Format
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### Error Format
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR | NOT_FOUND | SECURITY_VIOLATION | APPROVAL_REQUIRED",
    "message": "Human-readable explanation of error.",
    "details": {}
  }
}
```

---

## 4. REST API Endpoint Specifications

### A. System Status (`GET /api/v1/system/status`)
Powers the HUD top-bar system indicator ("SYSTEMS ONLINE", latency, version, and component status).

- **Method**: `GET`
- **Status Codes**: `200 OK`
- **Response Example**:
```json
{
  "success": true,
  "data": {
    "status": "online",
    "application": {
      "name": "FRIDAY-AI-Backend",
      "version": "0.1.0",
      "environment": "development",
      "uptime_seconds": 1420.5
    },
    "components": {
      "database": {
        "status": "online",
        "engine": "sqlite",
        "latency_ms": 1.2
      },
      "ai_provider": {
        "status": "online",
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "latency_ms": 24.5,
        "default_model": "gemma4:12b",
        "model_readiness": "ready",
        "available_models": ["gemma4:12b"]
      },
      "agent_runtime": {
        "status": "online",
        "max_steps": 10
      },
      "voice_provider": {
        "status": "online",
        "stt_engine": "whisper",
        "tts_engine": "say"
      },
      "browser_integration": {
        "status": "online",
        "engine": "playwright"
      },
      "filesystem_tool": {
        "status": "online",
        "approved_roots_count": 1
      },
      "terminal_tool": {
        "status": "online",
        "allowed_executables_count": 8
      },
      "websocket_service": {
        "status": "online",
        "active_connections": 1
      }
    },
    "timestamp": "2026-10-22T12:00:00"
  }
}
```

### B. Diagnostics & Capabilities
- `GET /api/v1/system/diagnostics`: Component latencies, missing configs, actionable fix advice.
- `GET /api/v1/system/capabilities`: Registered tool catalog, risk levels (`read_only`, `local_mutation`, `destructive`), and permission rules.
- `GET /api/v1/system/info`: Assistant identity branding ("FRIDAY AI - Tactical Defense HUD"), supported features list.

---

### C. Tactical Command Submission (`POST /api/v1/commands`)
Submits a user command text for natural-language agent orchestration or tool execution.

- **Request Body**:
```json
{
  "command": "Inspect workspace files and report test status",
  "conversation_id": "optional-uuid",
  "context": {},
  "response_mode": "sync",
  "locale": "en-US",
  "request_id": "client-uuid-for-idempotency"
}
```

- **Response Example**:
```json
{
  "success": true,
  "data": {
    "command_id": "76ba3f6e-1d54-469b-8d59-7f311c19b671",
    "task_id": "c018260a-4da2-4c28-912c-5526cbddca83",
    "run_id": "a90bbad3-e66b-4e09-b68f-395786438096",
    "status": "completed",
    "acknowledgment": "Tactical command accepted. Run a90bbad3 initiated.",
    "approval_required": false,
    "event_ref": "/api/v1/events?task_id=c018260a-4da2-4c28-912c-5526cbddca83",
    "result": {
      "summary": "Step 1 executed successfully.",
      "plan": { "steps": [...] },
      "error": null
    }
  }
}
```

---

### D. Central AI Visualizer State (`GET /api/v1/agent/state`)
Powers the animated circular HUD graphic. Reflects truthful backend activity.

- **Activity State Values**:
  - `idle`: Standing by for user prompt.
  - `listening`: Vocal audio input active.
  - `transcribing`: Processing speech-to-text.
  - `thinking`: Reasoning / model inference.
  - `planning`: Formulating multi-step execution plan.
  - `researching`: Document indexing / web research.
  - `executing_tool`: Executing validated agent tool action.
  - `running_terminal`: Subprocess execution underway.
  - `speaking`: Synthesizing voice speech.
  - `waiting_for_approval`: Action blocked awaiting user security consent.
  - `completed`: Operation completed successfully.
  - `error`: Failed operation with error description.
  - `cancelled`: Process cancelled by user.

- **Response Example**:
```json
{
  "success": true,
  "data": {
    "state": "executing_tool",
    "task_id": "c018260a-4da2-4c28-912c-5526cbddca83",
    "description": "Executing tool action (step 1/3)...",
    "current_step": 1,
    "total_steps": 3,
    "awaiting_approval": false,
    "last_successful_operation": "2026-10-22T11:58:20",
    "last_error_category": null,
    "updated_at": "2026-10-22T12:00:01"
  }
}
```

---

### E. Controlled Terminal Sessions (`/api/v1/terminal/*`)

Distinguishes natural-language AI tasks from explicit terminal command execution.

1. **Create Session**: `POST /api/v1/terminal/sessions`
   - Body: `{"working_directory": "/path/to/project", "profile_name": "system_check"}`
   - Profiles: `system_check`, `git_inspect`, `python_test`, `code_lint`
2. **Inspect Session**: `GET /api/v1/terminal/sessions/{session_id}`
3. **Execute Command**: `POST /api/v1/terminal/sessions/{session_id}/commands`
   - Body: `{"command": "git status"}`
   - Returns separate `stdout`, `stderr`, `exit_code`, and `execution_time_ms`.
4. **History**: `GET /api/v1/terminal/sessions/{session_id}/history`
5. **Cancel Active Process**: `POST /api/v1/terminal/sessions/{session_id}/cancel`
6. **Close Session**: `DELETE /api/v1/terminal/sessions/{session_id}`

---

### F. Voice & Audio Services (`/api/v1/voice/*`)

- `GET /api/v1/voice/capabilities`: Returns STT and TTS engine readiness.
- `GET /api/v1/voice/voices`: Lists selectable voices (e.g. `default`, `Samantha`, `Alex`).
- `POST /api/v1/voice/transcriptions`: Upload `multipart/form-data` audio file (`file`). Returns `{"transcript": "..."}`. Max size 25MB. Supported: `.wav`, `.mp3`, `.ogg`, `.webm`.
- `POST /api/v1/voice/speech`:
  - Body: `{"text": "Systems online.", "voice": "default", "speed": 1.0}`
  - Returns `audio/wav` binary byte stream for immediate HTML5 audio playback.

---

### G. Quick Actions Registry (`/api/v1/quick-actions`)

1. **List Actions**: `GET /api/v1/quick-actions`
   Predefined tactical buttons:
   - `diagnostics.run`: Run component diagnostics.
   - `system.status_summary`: Summarize status.
   - `capabilities.list`: List permission grants.
   - `model.info`: LLM readiness & weights.
   - `agent.activity`: Visualizer activity state.
   - `tasks.recent_history`: Recent execution history.
   - `assistant.explain`: Architecture & identity.
   - `assistant.help`: Supported commands guide.
2. **Execute Action**: `POST /api/v1/quick-actions/{action_id}/execute`

---

### H. Validated Settings (`/api/v1/settings`)

- **Get Active Settings**: `GET /api/v1/settings`
- **Partially Update Preferences**: `PATCH /api/v1/settings`
  ```json
  {
    "language": "en",
    "locale": "en-US",
    "theme": "stark_cyan",
    "selected_model": "gemma4:12b",
    "voice_provider": "local",
    "speech_speed": 1.0,
    "voice_input_enabled": true,
    "voice_output_enabled": true,
    "realtime_events_enabled": true,
    "terminal_profile": "system_check"
  }
  ```
- **Allowed Options**: `GET /api/v1/settings/options` (returns list of allowed languages, locales, themes, models, and voices).

---

## 5. Real-Time WebSocket HUD Event Bus

- **Endpoint**: `WS /api/v1/events`
- **Query Parameters**:
  - `user_id`: Defaults to `local_user`.
  - `token`: Optional API token if configured.
  - `since_event_id`: Optional event ID to replay missed events upon reconnection.

### Event Format Schema
```json
{
  "event_id": "4b684cb3-080c-43f1-b0db-6e6b52c03c53",
  "type": "agent.executing",
  "timestamp": "2026-10-22T12:00:00.123456",
  "task_id": "c018260a-4da2-4c28-912c-5526cbddca83",
  "correlation_id": null,
  "payload": {
    "state": "executing_tool",
    "description": "Executing tool action...",
    "current_step": 1,
    "total_steps": 3,
    "awaiting_approval": false
  }
}
```

### Event Names Catalog
| Category | Event Name | Payload Shape |
|---|---|---|
| **System** | `system.connected` | `{"connection_id": str, "agent_state": obj}` |
| **System** | `system.status` | `{"status": str, ...}` |
| **Visualizer** | `agent.idle` | `{"state": "idle", "description": str}` |
| **Visualizer** | `agent.thinking` | `{"state": "thinking", "description": str}` |
| **Visualizer** | `agent.planning` | `{"state": "planning", "description": str}` |
| **Visualizer** | `agent.executing` | `{"state": "executing_tool", "current_step": int, "total_steps": int}` |
| **Visualizer** | `agent.waiting_for_approval` | `{"state": "waiting_for_approval", "description": str}` |
| **Visualizer** | `agent.completed` | `{"state": "completed", "result": str}` |
| **Visualizer** | `agent.failed` | `{"state": "error", "error": str}` |
| **Command** | `command.accepted` | `{"command_id": str, "command_text": str}` |
| **Command** | `command.completed` | `{"run_id": str, "result": str}` |
| **Command** | `command.failed` | `{"run_id": str, "error": str}` |
| **Terminal** | `terminal.session_created` | `{"session_id": str, "working_directory": str}` |
| **Terminal** | `terminal.command_started` | `{"session_id": str, "executable": str, "args": list}` |
| **Terminal** | `terminal.command_output` | `{"session_id": str, "stdout": str, "stderr": str}` |
| **Terminal** | `terminal.command_completed` | `{"session_id": str, "exit_code": int, "execution_time_ms": int}` |
| **Voice** | `voice.listening_started` | `{}` |
| **Voice** | `voice.transcription_final` | `{"transcript": str, "mime_type": str}` |
| **Voice** | `voice.speech_started` | `{"text": str, "voice": str}` |
| **Voice** | `voice.speech_completed` | `{}` |
| **Voice** | `voice.error` | `{"error": str}` |
| **Security** | `approval.required` | `{"run_id": str, "summary": str}` |
| **Settings** | `settings.updated` | `{"updated_keys": list[str]}` |

### Client-to-Server Messages
- Send `{"type": "ping", "timestamp": "..."}` -> Backend replies `{"type": "pong", "timestamp": "..."}`.
- Send `{"type": "get_state"}` -> Backend replies with current `agent.*` event state.

---

## 6. Real vs Mocked Capabilities

- **Real & Verified**:
  - SQLite async database persistence with Alembic migrations.
  - Full-text document search with SQLite FTS5 index.
  - Multi-step agent orchestrator with planning and tool execution.
  - 24 system tools with sandboxing, RBAC capability grants, and policy enforcement.
  - Controlled subprocess execution with argument arrays, environment filtering, and command profiles.
  - Real-time WebSocket connection manager and event bus with reconnect ring buffer.
  - Persistent user settings and quick-action execution handlers.
- **Optional / Host-Dependent**:
  - Local Ollama AI provider: Connected if `ollama serve` is running on host; otherwise reports `degraded`/`offline` status truthfully without crashing.
  - Local Whisper STT: Active if `whisper` binary is on host PATH; otherwise reports `not_configured`.
  - Local Speech TTS: Active if `say` (macOS) or `espeak` (Linux) is available.
  - Playwright browser automation: Active if Chromium is installed.

---

## 7. Local Development Startup Instructions

1. **Activate Virtualenv & Start Server**:
   ```bash
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Verify System Status via Curl**:
   ```bash
   curl -s http://127.0.0.1:8000/api/v1/system/status | jq
   ```
3. **Submit Command via Curl**:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/v1/commands \
     -H "Content-Type: application/json" \
     -d '{"command": "Inspect workspace files"}' | jq
   ```
