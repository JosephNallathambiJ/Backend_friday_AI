# FRIDAY AI Backend
## Cyber Agent, Omni OSINT Power, Backend Diagnostics, Chatbot Mouth & Audio Services

Production-grade, modular, local-first backend for the personal AI work assistant **FRIDAY AI**.

---

## Table of Contents
- [A. FRIDAY Overview & Architecture](#a-friday-overview--architecture)
- [B. Dual-Brain Cognitive Architecture](#b-dual-brain-cognitive-architecture)
- [C. Cyber Agent & Target Authorization System](#c-cyber-agent--target-authorization-system)
- [D. Omni OSINT Power Integration Layer](#d-omni-osint-power-integration-layer)
- [E. Backend Diagnostics, Health Auditor & Workflow Validation](#e-backend-diagnostics-health-auditor--workflow-validation)
- [F. Chatbot Agent — FRIDAY's Mouth & Response Coordinator](#f-chatbot-agent--fridays-mouth--response-coordinator)
- [G. Microphone & Audio Processing Subsystem](#g-microphone--audio-processing-subsystem)
- [H. Complete Specialist Agent Directory (21 Specialist Roster)](#h-complete-specialist-agent-directory-21-specialist-roster)
- [I. Mathematical Engine & 16 Domain Inventory (Domains A to P)](#i-mathematical-engine--16-domain-inventory)
- [J. Algorithm Index](#j-algorithm-index)
- [K. API Reference](#k-api-reference)
- [L. Setup and Configuration](#l-setup-and-configuration)
- [M. Security, Privacy Boundaries & Limitations](#m-security-privacy-boundaries--limitations)
- [N. Testing, 3-Pass Debugging & Capability Matrix](#n-testing-3-pass-debugging--capability-matrix)
- [O. References and Licensing](#o-references-and-licensing)

---

## A. FRIDAY Overview & Architecture

FRIDAY AI is a modular, personal assistant backend engineered on a cyber-aware dual-brain architecture. It pairs an agentic Left Brain with a specialized cybersecurity Right Brain, coordinates conversational intent through a dedicated Chatbot agent ("FRIDAY's Mouth"), and delegates heavy operations to typed tools and deterministic engines.

### Core Architecture Principles
1. **The Models are the Brains, Not Authorities**: Central models interpret language, plan multi-step workflows, and format output. They cannot execute shell scripts, read private host files, or bypass guardrails without going through verified tools and policy checks.
2. **Chatbot Mouth as Transparent Coordinator**: `ChatbotAgent` receives frontend messages, determines whether a query is computational, defensive cyber, diagnostic, or general, and explains actions before high-impact operations. It never fabricates outcomes.
3. **Target Authorization Boundary**: Reconnaissance, port discovery, and active vulnerability probing require structured, user-approved `TargetAuthorization` tokens. Passive OSINT is permitted by default; intrusive active network probing without explicit authorization is strictly blocked.
4. **Isolated Integrations (Omni OSINT Power)**: Integrations with external OSINT providers operate through strongly-typed adapters with rate-limiting, credential redaction, provenance attribution, and offline mock modes.
5. **Backend Self-Diagnostics & Regression Testing**: `BackendDiagnosticsAgent` performs static AST analysis, critical import checks, database schema checks, API route inspection, dual-brain model health checks, and audio subsystem verification.
6. **Decoupled Audio Subsystem**: Microphone capture permissions belong strictly to the frontend client. The backend provides an ingestion and streaming speech-to-text / text-to-speech engine with ephemeral file cleanup.
7. **Strictly Backend-Only**: Zero frontend components, HTML, CSS, or React code. Exposes typed REST and WebSocket/SSE APIs for command-center user interfaces.

### High-Level System Architecture
```
                         +-----------------------------+
                         |      User / API Client      |
                         +--------------+--------------+
                                        | (Audio / Chat)
                         +--------------v--------------+
                         |  Chatbot Agent ("Mouth")    |
                         +--------------+--------------+
                                        |
                         +--------------v--------------+
                         |   Intent Classifier & Router|
                         +--------------+--------------+
                                        |
        +-------------------+-----------+-----------+-------------------+
        |                   |                       |                   |
        v                   v                       v                   v
+---------------+   +---------------+       +---------------+   +---------------+
|  Left Brain   |   |  Right Brain  |       | Mathematical  |   |    Backend    |
| LiquidAI LFM  |   | Dolphin3-Cyber|       |    Engine     |   |  Diagnostics  |
| (General Plan)|   | (Defensive Sec|       | (Deterministic|   | (Static+Health|
+-------+-------+   +-------+-------+       +-------+-------+   +-------+-------+
        |                   |                       |                   |
        +-------------------+-----------+-----------+-------------------+
                                        |
                         +--------------v--------------+
                         | Unified Policy & Auth Engine|
                         +--------------+--------------+
                                        |
        +-------------------------------+-------------------------------+
        |                               |                               |
        v                               v                               v
+-----------------------+   +-----------------------+   +-----------------------+
|  21 Specialist Agents |   |  Shared Tool Registry |   | Omni OSINT Adapter    |
| (Cyber, Coding, etc.) |   | (Files, Network, etc) |   | (Mock/Live, Redacted) |
+-----------------------+   +-----------------------+   +-----------------------+
        |                               |                               |
        +-------------------------------+-------------------------------+
                                        |
                         +--------------v--------------+
                         |  Target Authorization & Log |
                         +-----------------------------+
```

---

## B. Dual-Brain Cognitive Architecture

FRIDAY operates with two distinct locally hosted models served through **Ollama** (`http://127.0.0.1:11434`):

| Characteristic | Left Brain (General Agent) | Right Brain (Cyber Specialist) |
| :--- | :--- | :--- |
| **Model Repository** | [`LiquidAI/LFM2.5-2.6B-GGUF`](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF) | [`RavichandranJ/Dolphin3-Cyber-8B-GGUF`](https://huggingface.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF) |
| **Configured Identifier** | `LiquidAI/lfm2.5-2.6b:q4_k_m` | `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M` |
| **Detected Tag** | `hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M` | `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M` |
| **Quantization** | Q4_K_M (~1.7 GB) | Q4_K_M (~4.9 GB) |
| **Core Responsibilities** | Request interpretation, multi-step planning, tool selection, conversational synthesis | Defensive vulnerability triage, security reviews, attack-surface modeling, log triage |
| **Tool Calling** | Native Ollama tool calling with structured JSON fallback | Scoped tool calling with policy gating |
| **Config Variable** | `FRIDAY_LEFT_MODEL` | `FRIDAY_RIGHT_MODEL` |
| **Temperature** | 0.7 (`LEFT_MODEL_TEMPERATURE`) | 0.4 (`RIGHT_MODEL_TEMPERATURE`) |
| **Invocation Command** | `ollama run hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M` | `ollama run hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M` |

### Untrusted Model Output Handling
Outputs from both the Left Brain and Right Brain are treated as untrusted proposals. All tool invocations and side effects must pass through the `SecurityPolicyEngine` and `TargetAuthorizationManager` before any system or network call is executed.

---

## C. Cyber Agent & Target Authorization System

The `CyberAgent` (`app/agents/cyber_agent.py`) is FRIDAY's central defensive security specialist. It provides authorized attack-surface discovery, HTTP security audits, secret detection, dependency audits, and structured remediation reporting.

### Mandatory Target Authorization Rules
Every active scanning, reconnaissance, or diagnostic job must record:
- **`target`**: Target hostname, IP, CIDR, or local asset identifier.
- **`target_type`**: Domain, IP address, CIDR range, URL, local repository, or container.
- **`scope_reference`**: User-provided approval or formal asset-scope reference.
- **`allowed_techniques`**: Explicitly approved list of techniques (`passive_dns`, `http_security_headers`, `authorized_port_scan`, `secret_scan`, etc.).
- **`excluded_targets`**: Excluded subnet ranges or sensitive endpoints.
- **`rate_limit_rps` & `concurrency_limit`**: Configurable bandwidth and thread limits.
- **`operator` & `job_id`**: Audit identity and execution tracking ID.
- **`active_recon_permitted`**: Strict boolean guard. If `False` or missing, all active port probing and network intrusion tools return `PORT PROBING REJECTED`.

### Modular Cyber Tools
1. **`passive_domain_recon`** (`PassiveDomainReconTool`): DNS records (`A`, `AAAA`, `MX`, `TXT`, `NS`, `CNAME`), certificate transparency enumeration, and domain WHOIS metadata.
2. **`http_security_audit`** (`HttpSecurityAuditTool`): Header analysis (`HSTS`, `CSP`, `X-Content-Type-Options`, `X-Frame-Options`, `Permissions-Policy`), TLS protocol/cipher verification, and cookie flags (`Secure`, `HttpOnly`, `SameSite`).
3. **`authorized_port_discovery`** (`AuthorizedPortDiscoveryTool`): TCP port discovery with rate limits and active recon authorization checks.
4. **`dependency_audit`** (`DependencyAuditTool`): Python package vulnerability scanning against advisory feeds (`pip-audit` / PyPI advisory database).
5. **`secret_detection_scan`** (`SecretDetectionTool`): Static AST and regex scanning for unredacted API tokens, private keys, AWS secrets, and passwords.
6. **`generate_security_report`** (`SecurityReportTool`): Renders severity-ranked Markdown and JSON reports with remediation steps and rollback guidance.

---

## D. Omni OSINT Power Integration Layer

### Project Identity & Honest Connectivity Status
Inspection of the repository confirms that **Omni OSINT Power** refers to an external open-source intelligence aggregation service.

> **Honest Operational Status**:
> - **NOT CONNECTED** to a live remote provider by default because `OMNI_OSINT_ENDPOINT` and `OMNI_OSINT_API_KEY` are not configured in standard development environments.
> - **FULLY OPERATIONAL IN TYPED MOCK MODE**: The integration layer (`app/integrations/omni_osint/` and root `integrations/omni_osint/`) is fully implemented with a typed request/response contract, timeout enforcement, rate-limiting, and comprehensive mock datasets for domain recon, certificate transparency, and threat intelligence.

### Adapter Features (`OmniOSINTAdapter`)
- **Capability Discovery**: Discovers query types (`domain`, `ip`, `subdomain_enum`, `cert_transparency`, `whois`, `threat_intel`).
- **Health Checks**: Distinguishes `CONNECTED`, `NOT CONNECTED`, and `MOCK MODE`.
- **Sensitive Data Redaction**: Automatic scrubbing of Bearer tokens (`[REDACTED_TOKEN]`), API keys (`[REDACTED_KEY]`), passwords (`[REDACTED_PASSWORD]`), and email addresses (`[REDACTED_EMAIL]`).
- **Private Data Protection**: Actively rejects queries containing private local file paths (`/Users/`, `/etc/`, `C:\`) or private keys.
- **Attribution & Provenance**: Every intelligence item returns a `SourceAttribution` record containing source name, timestamps, confidence scores, and provider metadata.

---

## E. Backend Diagnostics, Health Auditor & Workflow Validation

The `BackendDiagnosticsAgent` (`app/agents/backend_diagnostics_agent.py`) and `SystemDiagnosticChecker` (`app/services/diagnostics/checker.py`) provide comprehensive health and regression audits across the codebase and runtime.

### Diagnostic Checks Implemented
1. **Python Syntax & AST Integrity**: Parses all 147 Python source files using `ast.parse` to detect syntax errors before runtime execution.
2. **Critical Module Imports**: Verifies that 11 core backend modules (`fastapi`, `sqlalchemy`, `pydantic`, `ollama`, `sympy`, `numpy`, `uvicorn`, etc.) load without circular dependencies.
3. **Configuration & Environment Validation**: Confirms essential runtime variables and warns if models or endpoints are misconfigured.
4. **API Route Collision Inspection**: Iterates over all registered FastAPI routes and flags collision candidates or route overlap.
5. **Database Connectivity & Health**: Executes an asynchronous `SELECT 1` against the SQLite/Alembic database engine and validates table access.
6. **Tool and Specialist Registries**: Asserts presence and valid schemas for all 40 registered tools and 21 specialist agents.
7. **Dual-Brain Model Status**: Connects to the local Ollama instance (`http://127.0.0.1:11434`), checks reachability, and inspects installed model tags.
8. **Audio Subsystem Readiness**: Tests temporary directory permissions, detects local STT fallback capability, and verifies TTS binary availability (`/usr/bin/say`).

### Supported Job Types
- `diagnose`: Fast runtime health checks.
- `debug`: Detailed error clustering and root-cause hypothesis generation.
- `test_workflow`: End-to-end task pipeline validation from user input to tool execution.
- `audit_backend`: Complete static and runtime compliance audit.
- `verify_fix`: Regression check to verify whether a patch fixed an identified finding.

---

## F. Chatbot Agent — FRIDAY's Mouth & Response Coordinator

`ChatbotAgent` (`app/agents/chatbot_agent.py`) is FRIDAY's conversational interface. It receives incoming messages from API clients or the frontend HUD, manages conversation sessions, and coordinates delegation without pretending to have executed actions it has not performed.

### Intent Classification & Routing Matrix
```
User Message
     |
     +---> [Math Keywords / Numerics]  ---> MathematicalEngine (Deterministic)
     |
     +---> [Cyber / Recon / Ports]     ---> CyberAgent (Right Brain Dolphin3)
     |
     +---> [Diagnostics / Health]      ---> BackendDiagnosticsAgent
     |
     +---> [General Queries / Tasks]   ---> FridayBrain Orchestrator (Left Brain LFM)
```

### Fact Transparency
Every response returned by `ChatbotAgent` contains:
- `content`: User-facing markdown message.
- `summary`: Concise one-line status summary.
- `routing`: The primary agent selected and the reasoning.
- `verified_facts`: Confirmed execution evidence from tools.
- `hypotheses`: Model-suggested possibilities clearly marked as unconfirmed.
- `unknowns`: Explicit gaps where information is missing.

---

## G. Microphone & Audio Processing Subsystem

### Permission Model
- **Frontend / Platform Responsibility**: Operating system and browser microphone capture permissions belong strictly to the frontend application.
- **Backend Responsibility**: Ingestion of uploaded audio files (`POST /api/v1/audio/transcriptions`), real-time WebSocket streaming (`WS /api/v1/audio/stream`), speech-to-text processing, and optional text-to-speech synthesis (`POST /api/v1/audio/synthesize`).

### Architectural Pipeline
```
Microphone Audio (Frontend)
          |
   (Audio File / WS Stream)
          |
          v
   Audio Validation & Size Bounds (Max 25 MB)
          |
          v
   Speech-to-Text (Whisper CLI or Local Fallback)
          |
          v
   Chatbot Agent (Mouth & Coordinator)
          |
          v
   Specialist Agent / Engine Execution
          |
          v
   Optional Text-to-Speech (macOS `say` / Synthesizer)
          |
          v
   Frontend Output
```

### Privacy & Data Retention Controls
- **Immediate Ephemeral Cleanup**: All temporary audio files created during upload or streaming are immediately deleted upon transcription completion (`retained_on_disk=False`).
- **Opt-In Long Term Retention**: Audio recordings are never retained on disk unless `AUDIO_RETENTION_ENABLED=true` is explicitly set by the user.
- **Sanitized Logging**: Raw audio waveforms, binary chunks, and private transcripts are excluded from standard logging.

---

## H. Complete Specialist Agent Directory (21 Specialist Roster)

All 21 agents inherit from `BaseSpecialistAgent` and are centrally registered in `SpecialistRegistry`:

| # | Agent Name | Agent ID | Core Responsibilities | Available Tools | Status |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Chatbot Mouth & Coordinator** | `chatbot` | Conversational interface, intent classification, specialist delegation, and evidence summarization. | `run_diagnostics`, `passive_domain_recon`, `calculate` | **AVAILABLE** |
| **2** | **Cybersecurity Specialist** | `cyber_agent` | Attack surface discovery, passive OSINT, HTTP security audits, secret detection, and port probing. | `passive_domain_recon`, `http_security_audit`, `authorized_port_discovery`, `dependency_audit`, `secret_detection_scan` | **AVAILABLE** |
| **3** | **Backend Diagnostics Agent** | `backend_diagnostics` | System health auditing, static code checks, runtime tests, workflow validation, and report generation. | `run_diagnostics`, `get_system_info`, `read_file` | **AVAILABLE** |
| **4** | **Coding Agent** | `coding` | Analyzes codebases, generates patches, conducts reviews, and refactors within approved directories. | `read_file`, `write_file`, `search_files`, `git_status`, `git_diff`, `run_command` | **AVAILABLE** |
| **5** | **Terminal Agent** | `terminal` | Executes registered commands via argument arrays (`shell=False`), captures outputs, and tracks history. | `run_command` | **AVAILABLE** |
| **6** | **Privileged Operations Agent** | `privileged` | Evaluates requests requiring elevation, checks explicit allowlists, and enforces human approvals. | `run_command`, `run_diagnostics` | **AVAILABLE** |
| **7** | **Legacy Cyber Agent** | `cybersecurity` | Static vulnerability analysis, dependency risk assessments, and secret scanning. | `security_scan`, `search_files`, `read_file` | **AVAILABLE** |
| **8** | **Web Research Agent** | `research` | Permitted web searches, content summarization, and capability-gap identification. | `web_search`, `fetch_webpage` | **AVAILABLE** |
| **9** | **Administration Agent** | `administration` | Configuration inspection, service diagnostics, and administrative workflows. | `get_system_info`, `run_diagnostics` | **AVAILABLE** |
| **10** | **Computation Agent** | `computation` | Deterministic calculations, statistical computing, structured transformations, and equations. | `calculate`, `simplify_expression`, `solve_equation`, `differentiate`, `integrate`, `compute_matrix` | **AVAILABLE** |
| **11** | **Talking Agent** | `talking` | Conversational voice, speech command routing, and voice diagnostics. | `send_notification` | **AVAILABLE** |
| **12** | **Pattern Recognition Agent** | `pattern_recognition` | Text/log anomaly detection, clustering, trend analysis, and confidence scoring. | `read_file`, `search_files` | **AVAILABLE** |
| **13** | **Learning Agent** | `learning` | Manages user preferences, tracks workflow patterns, and proposes inspectable skill improvements. | `read_file`, `write_file` | **AVAILABLE** |
| **14** | **GitHub Skill Acquisition Agent** | `skill_acquisition` | Discovers GitHub repositories, manages quarantine cloning, runs security scanners, and installs skills. | `web_search`, `fetch_webpage` | **AVAILABLE** |
| **15** | **Browsing Agent** | `browser` | Controls isolated browser sessions, extracts page content, and requests approval for actions. | `browser_navigate`, `browser_read`, `browser_interact`, `browser_close` | **AVAILABLE** |
| **16** | **Management Agent** | `management` | Coordinates multi-agent subtasks, tracks dependencies, and aggregates outputs. | `get_system_info` | **AVAILABLE** |
| **17** | **Testing and QA Agent** | `testing` | Validates skills in isolation, verifies tool schemas, and executes unit test suites. | `run_command`, `read_file` | **AVAILABLE** |
| **18** | **Documentation Agent** | `documentation` | Parses repository documentation, generates internal usage guides, and documents tool schemas. | `read_file`, `write_file`, `search_files` | **AVAILABLE** |
| **19** | **Data & Memory Agent** | `data_memory` | Indexes authorized documents, retrieves relevant task history, and manages knowledge context. | `read_file`, `search_files` | **AVAILABLE** |
| **20** | **Integration Agent** | `integration` | External API adapter integration, health checks, structured retries, and token isolation. | `web_search`, `fetch_webpage` | **AVAILABLE** |
| **21** | **Scheduler & Automation Agent** | `scheduler` | Manages cron and interval background jobs and tracks scheduled runs. | `get_system_info` | **AVAILABLE** |

---

## I. Mathematical Engine & 16 Domain Inventory

The deterministic math engine (`app/math/`) operates with safe AST parsing (no `eval()` / `exec()`), a 10-second computation ceiling, and residual validation:

- **Domain A — Arithmetic & Number Systems**: Prime factoring, Euclidean GCD/LCM, arbitrary-precision rationals, radix conversion.
- **Domain B — Algebra**: Symbolic expression simplification, polynomial factoring, equation solving with residual validation.
- **Domain C — Geometry & Trigonometry**: Heron's formula, Euclidean 2D distance, circle/triangle geometry.
- **Domain D — Calculus**: Symbolic derivatives, indefinite & definite integrals (Risch algorithm), limits, Taylor series.
- **Domain E — Linear Algebra**: Matrix inversion, determinant, eigenvalues/eigenvectors, linear system solving ($Ax=b$).
- **Domain F — Discrete Mathematics**: Combinatorics, permutations, combinations, recurrence relations.
- **Domain G — Probability**: Bayes' theorem posterior calculation, binomial distribution PMF/CDF.
- **Domain H — Statistics**: Mean, median, sample variance, standard deviation, ordinary least squares linear regression ($R^2$).
- **Domain I — Numerical Methods**: Bisection root finding, Newton-Raphson iteration.
- **Domain J — Optimization**: 1D Golden-Section search, local minima finding.
- **Domain K — Information Theory & Cryptography**: Shannon entropy, modular exponentiation, modular inverse.
- **Domain L — Financial Mathematics**: Compound interest, loan amortization annuities.
- **Domain M — Physics & Engineering**: Unit conversion (metric/imperial), kinematics, Ohm's law.
- **Domain N — Data Science & Machine Learning**: Classification metrics (Accuracy, Precision, Recall, F1), vector distance norms.
- **Domain O — Signal Processing**: 1D Fast Fourier Transform (Cooley-Tukey), linear convolution.
- **Domain P — Logic & Proofs**: Boolean logic simplification, exhaustive truth tables, tautology/contradiction proofs.

---

## J. Algorithm Index

| Algorithm | Domain | Implementation | File |
| :--- | :--- | :--- | :--- |
| **AST Code & Expression Parsing** | Safety | Python `ast.walk` validator | `app/math/parser.py` |
| **Target Scope Validation** | Security | Prefix & CIDR range matching | `app/security/target_authorization.py` |
| **Secret Detection Scanner** | Security | Regex token patterns & entropy checks | `app/tools/cyber_tools.py` |
| **HTTP Security Header Audit** | Security | OWASP secure header compliance check | `app/tools/cyber_tools.py` |
| **Port Probing Engine** | Security | Non-blocking async TCP connect | `app/tools/cyber_tools.py` |
| **Data Redaction Masker** | OSINT / Privacy | Regular expression token & email mask | `app/integrations/omni_osint/adapter.py` |
| **Diagnostic AST Syntax Scanner**| Diagnostics | Recursive AST syntax check across repository | `app/services/diagnostics/checker.py` |
| **Euclidean Algorithm (GCD/LCM)** | A. Arithmetic | `math.gcd`, `math.lcm` | `app/math/domains.py` |
| **Symbolic Differentiation** | D. Calculus | `sympy.diff` | `app/math/domains.py` |
| **Matrix Inversion with Residual**| E. Linear Algebra| `numpy.linalg.inv` + $\|AA^{-1}-I\|$ | `app/math/domains.py` |
| **Fast Fourier Transform (FFT)** | O. Signals | `numpy.fft.fft` | `app/math/domains.py` |
| **Truth Table Generator** | P. Logic | $2^n$ binary valuations + `sympy.simplify_logic` | `app/math/domains.py` |

---

## K. API Reference

All endpoints are versioned under `/api/v1` with convenient aliases exposed under `/api/*`:

### 1. Chatbot & Orchestration APIs
- `POST /api/chat`: Top-level chat turn processed through `ChatbotAgent` coordinator.
  ```json
  // Request
  {
    "message": "Calculate 42 * 17 + 256",
    "conversation_id": "conv-user-01"
  }
  // Response
  {
    "success": true,
    "data": {
      "content": "Result: **970**\n\nComputation confirmed via deterministic evaluation.",
      "summary": "Mathematical computation evaluated deterministically.",
      "routing": {
        "primary_agent": "math_engine",
        "intent_category": "mathematical_computation",
        "confidence": 0.98
      },
      "verified_facts": ["Exact result: 970"],
      "hypotheses": [],
      "unknowns": []
    }
  }
  ```
- `POST /api/v1/chat/coordinator`: Dedicated endpoint for structured coordinator responses.

### 2. Audio & Speech Processing APIs
- `POST /api/v1/audio/transcriptions` (or `POST /api/audio/transcriptions`): Upload and transcribe audio files.
  - Accepts multipart form data with audio bytes (`.wav`, `.mp3`, `.ogg`, `.m4a`, `.webm`).
  - Returns `{"transcript_id": "stt-...", "transcript": "...", "duration_seconds": 1.2, "retained_on_disk": false}`.
- `WS /api/v1/audio/stream` (or `WS /api/audio/stream`): Real-time bidirectional streaming audio WebSocket.
  - Send binary chunks or control JSON `{"command": "finalize"}` / `{"command": "cancel"}`.
- `POST /api/v1/audio/synthesize`: Text-to-speech audio generation.
  - Body: `{"text": "FRIDAY operational. All systems nominal.", "voice": "Samantha"}`.
  - Returns WAV audio stream.
- `GET /api/v1/audio/health`: Audio provider availability and engine status.

### 3. Cybersecurity & Target Authorization APIs
- `POST /api/v1/cyber/authorizations`: Register a new target authorization.
  - Body: `{"target": "127.0.0.1", "target_type": "ip_address", "scope_reference": "INTERNAL_PENTEST_SCOPE", "allow_active_recon": true, "allowed_techniques": ["authorized_port_scan"]}`.
- `GET /api/v1/cyber/authorizations`: List active scan authorizations.
- `POST /api/v1/cyber/investigate`: Run authorized cyber investigation.
- `POST /api/v1/cyber/report`: Generate security audit report in Markdown and JSON.

### 4. Backend Diagnostics & Health APIs
- `POST /api/v1/diagnostics/run` (or `POST /api/diagnostics/run`): Trigger diagnostics job.
  - Body: `{"job_type": "audit_backend"}` (or `diagnose`, `debug`, `test_workflow`, `verify_fix`).
  - Returns: `{"job_id": "diag-...", "status": "running" | "passed", "checks": [...], "markdown_report": "..."}`.
- `GET /api/v1/diagnostics/{job_id}`: Retrieve diagnostic report and check breakdown.
- `POST /api/v1/diagnostics/{job_id}/cancel`: Abort a running diagnostic job.
- `GET /health`: Fast service health check (`{"status": "ok"}`).
- `GET /ready`: Readiness probe verifying database and Ollama availability.

---

## L. Setup and Configuration

### Prerequisites
- Python 3.12+ (managed with `uv`)
- Ollama running locally:
  ```bash
  ollama serve
  ```
- Pull both brain models:
  ```bash
  # Left Brain (General Reasoning & Planning)
  ollama run hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M

  # Right Brain (Cybersecurity Specialist)
  ollama run hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M
  ```

### Environment Configuration (`.env`)
```bash
APP_NAME=FRIDAY-AI-Backend
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
DATABASE_URL=sqlite+aiosqlite:///friday.db

# Dual-Brain Configuration
FRIDAY_MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
FRIDAY_LEFT_MODEL=LiquidAI/lfm2.5-2.6b:q4_k_m
FRIDAY_RIGHT_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M
FRIDAY_DEFAULT_BRAIN=left
FRIDAY_CYBER_BRAIN_ENABLED=true
FRIDAY_DUAL_BRAIN_MODE=selective
FRIDAY_ALLOW_CLOUD_FALLBACK=false

# Omni OSINT Power Configuration
OMNI_OSINT_ENDPOINT=https://api.omni-osint.local/v1
OMNI_OSINT_API_KEY=your_optional_api_key_here
OMNI_OSINT_MOCK_MODE=true
OMNI_OSINT_TIMEOUT=15.0

# Audio & Speech Processing
AUDIO_TEMP_DIR=/tmp/friday_audio
AUDIO_MAX_SIZE_BYTES=26214400
AUDIO_RETENTION_ENABLED=false
```

### Installation & Startup
```bash
# Sync dependencies
uv sync --extra dev

# Run database migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## M. Security, Privacy Boundaries & Limitations

1. **Passive vs Active Reconnaissance**: Public DNS and certificate transparency intelligence are non-intrusive and permitted for research. Port scanning and network probing are actively blocked unless an explicit `TargetAuthorization` record is registered.
2. **Audio Data Privacy**: Audio recordings are never retained beyond the duration of transcription unless the user explicitly configures `AUDIO_RETENTION_ENABLED=true`. Transcripts and raw audio are omitted from system logs.
3. **OSINT Credential Protection**: The Omni OSINT adapter automatically masks bearer tokens, private keys, passwords, and user email addresses before outputs are rendered or stored.
4. **Local Execution**: All inference runs locally through Ollama. No user prompt, transcript, or source file is transmitted to cloud AI providers.
5. **No Shell Injections**: System processes execute via explicit argument lists (`subprocess.create_subprocess_exec` with `shell=False`).

---

## N. Testing, 3-Pass Debugging & Capability Matrix

### Rigorous 3-Pass Debugging Cycle
Per system engineering guidelines, all integrated components pass through a three-stage debugging verification cycle:
- **Pass 1: Automated Pytest Suite**: Full test execution across unit, integration, and scenario tests (**126 passed, 0 failed in 9.28s**).
- **Pass 2: System Diagnostic Audit**: Automated execution of all 8 system diagnostic checks (AST parsing of 147 files, module imports, route collisions, database health, registries, Ollama model reachability, and audio subsystem).
- **Pass 3: End-to-End Workflow Execution**: Live verification of Chatbot intent classification, Cyber Target Authorization blocking, Omni OSINT mock intelligence, audio ingestion, speech synthesis, and workflow job execution.

### Running Test Commands
```bash
# Run all tests
uv run pytest

# Run cyber agent and OSINT tests
uv run pytest tests/unit/test_cyber_agent_and_osint.py

# Run diagnostics tests
uv run pytest tests/unit/test_backend_diagnostics.py

# Run chatbot and audio integration tests
uv run pytest tests/integration/test_chatbot_and_audio.py

# Run code style and lint check
uv run ruff check .
```

### Capability Matrix

| Subsystem / Capability | Status | Required Dependency | Verification Method |
| :--- | :--- | :--- | :--- |
| **Left Brain (General Agent)** | **Implemented and tested** | Ollama, LiquidAI GGUF | Live model generation + test suite |
| **Right Brain (Cyber Specialist)** | **Implemented and tested** | Ollama, Dolphin3-Cyber GGUF | Live model review + test suite |
| **Dual-Brain Collaboration** | **Implemented and tested** | Ollama, both models | Integration workflow test |
| **Chatbot Mouth Coordinator** | **Implemented and tested** | FastAPI, SQLite | Intent classification + chat tests |
| **Target Authorization Boundary** | **Implemented and tested** | Python domain models | Active scan blocking unit tests |
| **Cyber Agent Specialist** | **Implemented and tested** | Network socket, AST | Cyber scan unit & integration tests |
| **Omni OSINT Integration (Mock)**| **Implemented and tested** | `httpx`, Pydantic | Health, query & redaction tests |
| **Omni OSINT (Live Provider)** | **Requires configuration** | Remote endpoint + API key | Mock mode active; live requires credentials |
| **Backend Diagnostics Agent** | **Implemented and tested** | Python `ast`, SQLite | 8-check diagnostic test suite |
| **Audio File Ingestion (STT)** | **Implemented and tested** | Local Whisper / Fallback | Synthetic audio transcription tests |
| **Speech Synthesis (TTS)** | **Implemented and tested** | macOS `say` / WAV gen | Audio synthesis tests |
| **Streaming Audio WebSocket** | **Implemented and tested** | FastAPI WebSockets | Chunk streaming integration tests |
| **Mathematical Engine (16 Domains)**| **Implemented and tested** | `sympy`, `numpy`, `mpmath` | Complete mathematical test suite |
| **GitHub Skill Acquisition** | **Implemented and tested** | `git`, `httpx` | Quarantine sandbox tests |
| **Tactical Command-Center HUD** | **Implemented and tested** | FastAPI WebSockets/SSE | Real-time event bus integration tests |
| **Docker Sandboxing for Skills** | *Planned* | Docker / Podman daemon | Manual review fallback active |

---

## O. References and Licensing

- **LiquidAI LFM2.5**: [LiquidAI LFM2.5 Model Card](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF). Licensed under LiquidAI model terms.
- **Dolphin3-Cyber 8B**: [Dolphin3-Cyber Model Card](https://huggingface.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF). Trained by RavichandranJ.
- **Ollama**: [Ollama Official Site](https://ollama.ai).
- **SymPy**: [SymPy: Symbolic Mathematics in Python](https://www.sympy.org). BSD-3-Clause license.
- **NumPy**: [NumPy: Scientific Computing](https://numpy.org). BSD-3-Clause license.
- **FastAPI**: [FastAPI Framework](https://fastapi.tiangolo.com). MIT license.
- **FRIDAY AI Backend**: Implementation codebase licensed under the MIT License.
# Backend_friday_AI
