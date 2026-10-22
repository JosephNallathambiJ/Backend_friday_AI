# FRIDAY AI Security Model & Policy

## 1. Threat Model & Trust Boundaries

FRIDAY AI operates as a local assistant with access to local filesystem resources and process execution capabilities. The system assumes:
1. **Model Output is Untrusted**: AI-generated responses and tool parameters are treated as untrusted input. The model cannot bypass authorization checks, cannot invent tools, and cannot invoke arbitrary Python functions.
2. **Retrieved Documents are Untrusted**: Content extracted from indexed files, Git repositories, or external URLs is sanitized. Direct instructions inside retrieved files cannot alter system policies (Prompt Injection Defense).
3. **Local Network Exposure**: By default, the application binds exclusively to the loopback interface (`127.0.0.1`). External LAN exposure is disabled.

---

## 2. Filesystem Boundary Enforcement (`app/security/path_validation.py`)

- **Strict Boundary Check**: Every file read, write, or search operation is validated against approved `ProjectDirectoryGrant` records.
- **Canonical Path Resolution**: All paths are resolved to their absolute real paths using `Path.resolve()` before checks, completely neutralizing `..` path traversal sequences.
- **Symlink Escape Defense**: Any symbolic link whose target resolves outside the approved project root is rejected.
- **Sensitive Path Denylist**: Files and directories matching the following patterns are unconditionally denied access during search and indexing:
  - Version control directories: `.git`, `.svn`
  - Secrets & keys: `*.pem`, `*.key`, `*.token`, `.env*`
  - Python / dependency environments: `.venv`, `node_modules`, `__pycache__`

---

## 3. Terminal Command Execution Policy (`app/security/command_policy.py`)

- **Argument Array Execution**: Commands are executed using `asyncio.create_subprocess_exec` with explicit argument lists (`argv`), ensuring `shell=False`. This eliminates shell injection vulnerabilities.
- **Strict Binary Allowlist**: Only pre-approved development executables may be run (e.g., `git`, `python`, `pytest`, `ruff`, `ls`).
- **Prohibited Executables**: Elevated and destructive commands are blocked unconditionally at the policy level:
  - `sudo`, `su`, `doas`
  - `rm`, `rmdir`, `dd`, `mkfs`
  - `chmod`, `chown`
- **Shell Metacharacter Rejection**: Any command string containing shell redirection, piping, or backgrounding operators (`|`, `;`, `&`, `>`, `<`, `$`, `` ` ``) is rejected.

---

## 4. Human-In-The-Loop Approval Workflow (`app/services/approval_service.py`)

Tools classified as `HIGH` or `CRITICAL` risk (e.g., terminal command execution, consequential file modifications) cannot be executed autonomously by the AI:
1. The orchestration engine pauses execution and creates a persistent `ApprovalRequest` record in the database.
2. The task enters the `awaiting_approval` state.
3. An authorized human must explicitly review the action preview and approve it via `/api/v1/approvals/{approval_id}/decision`.
4. Approvals are single-use, race-condition protected, and bound to the exact validated tool arguments.

---

## 5. Credential Sanitization & Audit Logging

- **Logging Redaction**: All log entries and diagnostic outputs are passed through the `mask_credentials()` utility, which uses regular expression patterns to mask bearer tokens, passwords, and private keys.
- **Audit Logging**: Every project registration, tool execution, approval decision, and security finding is written to the immutable `audit_events` database table.
