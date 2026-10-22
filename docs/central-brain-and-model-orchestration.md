# Central Brain Model and Unified Agent Orchestration

## 1. Overview

FRIDAY AI uses **`LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M`**, served via the local [Ollama](http://127.0.0.1:11434) installation, as its central reasoning and tool-orchestration brain.

The central brain (`FridayBrain`) is the single authoritative reasoning engine that:
1. Understands user intents and tactical goals.
2. Formulates execution plans.
3. Selects tools dynamically under least-privilege principles.
4. Coordinates specialist capabilities (Research, Filesystem, Browser, Terminal, Contacts, Device, Voice, Workflow).
5. Enforces security policies, capability verification, and human confirmation gates.
6. Evaluates and sanitizes tool observations as untrusted data.
7. Synthesizes final user responses.

---

## 2. Model Configuration & Provider

### Configuration Variables (`.env`)
| Variable | Default Value | Description |
|---|---|---|
| `FRIDAY_MODEL_PROVIDER` | `ollama` | Provider backend (`ollama`). No silent cloud fallback. |
| `FRIDAY_MODEL_NAME` | `LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M` | Canonical model tag. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama REST endpoint. |
| `MODEL_REQUEST_TIMEOUT` | `120.0` | Maximum request duration in seconds. |
| `MODEL_MAX_TOKENS` | `4096` | Generation prediction token limit. |
| `MODEL_TEMPERATURE` | `0.7` | Sampling temperature. |
| `MODEL_CONTEXT_LIMIT` | `16384` | Context window token budget. |
| `MODEL_MAX_CONCURRENCY` | `4` | Maximum parallel model invocations. |

### Tag Resolution & Normalization
Ollama tags differ across environments. The `OllamaProvider.resolve_installed_model_name()` method probes the Ollama API (`/api/tags`) and automatically normalizes canonical tags:
- `LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M` <-> `hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M`.

If the configured model is absent or Ollama is offline, FRIDAY raises an actionable `ModelNotInstalledError` or `ModelUnavailableError` with instructions to install the model rather than silently degrading or falling back to cloud.

---

## 3. Model Installation & Verification Commands

### Manual Model Setup
```bash
# Start Ollama service (if not running)
ollama serve

# Pull and run the LiquidAI model
ollama run hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M
```

### Verification Commands
```bash
# 1. Verify Ollama is reachable and model tag is present
curl -s http://127.0.0.1:11434/api/tags | jq '.models[].name'

# 2. Run FRIDAY model diagnostic suite via HTTP
curl -s http://localhost:8000/api/v1/system/diagnostics/model | jq .

# 3. Run automated diagnostic suite via CLI
uv run python -c "
import asyncio
from app.services.model_diagnostic_service import ModelDiagnosticService
report = asyncio.run(ModelDiagnosticService.run_diagnostics())
print('Status:', report.overall_status)
"
```

---

## 4. Model Capability Diagnostics

The diagnostic endpoint `GET /api/v1/system/diagnostics/model` evaluates 6 independent capabilities:

1. **`ollama_reachable`**: Validates HTTP connectivity to the local Ollama REST service.
2. **`model_installed`**: Verifies exact or normalized tag presence in the local model manifest.
3. **`simple_prompt_response`**: Confirms basic completion generation within token limits.
4. **`structured_tool_calling`**: Validates native Ollama tool-calling schema and arguments output.
5. **`tool_result_followup`**: Verifies model synthesizes follow-up responses when tool results are injected into context.
6. **`timeout_and_error_handling`**: Validates timeout boundaries and error reporting.

---

## 5. Central Brain Interface (`FridayBrain`)

`FridayBrain` (`app/services/brain_service.py`) provides the unified orchestration API:

- `respond_to_user(session, conversation_id, message, ...)`: Conversational turn handling.
- `plan_task(session, goal, ...)`: Decomposes goal into structured plan and assigns specialist.
- `select_tools(task_type, user_request)`: Applies least privilege tool selection based on intent.
- `execute_tool_calling_loop(session, initial_prompt, ...)`: Bounded native model-tool loop.
- `sanitize_tool_result(tool_name, raw_result, max_chars)`: Bounds and sanitizes output as untrusted external observation.
- `continue_task(session, task_id, approval_resolution)`: Resumes execution after security approval or cancellation.
- `interpret_tool_result(tool_name, raw_result)`: Human-readable synopsis generation.
- `synthesize_results(task_id, steps, tool_results)`: Summarizes completed operations.

---

## 6. Shared Specialist Agents

Specialist agents are capabilities coordinated by the Central Brain, registered in `SpecialistRegistry` (`app/agents/specialists/specialists.py`):

1. **Research Specialist**: Web searches, content extraction, and source synthesis.
2. **Filesystem Specialist**: Atomic file reading, writing, searching, and metadata inspection.
3. **Browser Specialist**: Headless DOM navigation, element interaction, and screenshot verification.
4. **Terminal Specialist**: Developer command execution under strict executable profiles.
5. **Contacts Specialist**: Address book search, contact creation, and email discovery.
6. **Device Specialist**: System telemetry (CPU, battery, OS) and notifications.
7. **Voice Specialist**: Audio synthesis, voice configuration, and speech command parsing.
8. **Workflow Specialist**: Complex multi-step task chaining and state persistence.

All specialists enforce the central `SecurityPolicyEngine` and `ToolRegistry`. Unregistered tools cannot be executed.

---

## 7. Bounded Tool-Calling Loop & Anti-Looping

The tool execution loop enforces strict safety boundaries:
- **Iteration Budget**: Capped at `max_iterations` (default 5-10).
- **Anti-Loop Duplicate Detection**: Each tool call fingerprint (`tool_name:sorted_json(args)`) is tracked. If the model proposes an identical call with identical arguments in the same turn, execution is rejected and loop feedback is injected.
- **Untrusted Observation Sanitization**: All tool outputs are truncated to `MAX_TOOL_OUTPUT_CHARS` (4,000 characters) and marked as untrusted observations to prevent prompt injections.
- **Human Approval Pause**: Any tool flagged with `requires_approval=True` or `ToolRiskLevel.DESTRUCTIVE` creates an `ApprovalRequest` and pauses the task until explicit user approval is granted.

---

## 8. Real-Time HUD Event Contract

During reasoning and execution, `FridayBrain` publishes real-time events to the HUD WebSocket bus:
- `command.request_received`: Tactical command received.
- `agent.planning_started`: Goal decomposition initiated.
- `agent.plan_created`: Structured plan created with estimated steps.
- `agent.tool_selected`: Tools selected under least privilege.
- `agent.tool_started`: Tool execution began with parameters.
- `agent.tool_completed`: Tool returned structured observation.
- `agent.approval_required` / `approval.required`: Execution paused awaiting security confirmation.
- `agent.task_resumed`: Resumed following approval decision.
- `command.task_completed`: Task concluded with final synthesized response.
- `command.task_failed`: Task halted due to error.
- `agent.task_cancelled`: User rejected approval or requested cancellation.

---

## 9. Error Hierarchy

The system distinguishes between specific error categories:
- `ModelUnavailableError` (HTTP 503): Ollama service unreachable.
- `ModelNotInstalledError` (HTTP 503): Configured model missing from Ollama.
- `ModelTimeoutError` (HTTP 504): Inference request timed out.
- `MalformedToolCallError` (HTTP 422): Tool call arguments cannot be parsed or validated.
- `ToolUnavailableError` (HTTP 404): Requested tool is unregistered or disabled.
- `SecurityPolicyError` (HTTP 403): Operation blocked by capability permissions or missing grant.
- `ApprovalRequiredError` (HTTP 403): Action paused awaiting human confirmation.
- `TaskBudgetExhaustedError` (HTTP 429): Loop reached maximum iteration budget.
