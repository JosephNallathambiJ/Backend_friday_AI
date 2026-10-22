# Complete Security Model & Privilege Management

## 1. Zero Trust Architecture

FRIDAY AI operates under a Zero Trust model regarding both external inputs and AI model outputs:
1. **The LLM is Never an Authority**: Model-generated tool calls, parameters, and proposals are untrusted requests. Every call must pass through the `PolicyEngine`.
2. **Untrusted Data Isolation**: Files retrieved from disk, internet search results, and scraped webpages are treated as passive data. Embedded prompt injections cannot elevate permissions.
3. **No Unrestricted Shell**: Shell commands are executed via `asyncio.create_subprocess_exec` using argument arrays (`argv`) with `shell=False`. Arbitrary shell text endpoints do not exist.

## 2. Privileged Tool Gateway (`app/security/privileged.py`)

FRIDAY AI avoids running with administrative (`root`) privileges. For operations requiring elevation:
- A dedicated, narrow allowlist of operations is enforced (`network.flush_dns`, `system.time_sync_status`, `system.service_status`).
- Arbitrary privilege escalation and root shells are strictly prohibited.
- If elevation is not configured or permitted, an explicit structured error is returned.

## 3. Defense-in-Depth Checklist

- [x] **Path Traversal**: Canonical path resolution via `Path.resolve()`, symlink escape blocking, sensitive file denylist.
- [x] **SSRF Protection**: Private, loopback, link-local, and reserved IP blocking with redirect re-verification.
- [x] **Command Injection**: Subprocess argument arrays (`shell=False`), executable allowlists, argument metacharacter filtering.
- [x] **Credential Leakage**: Regex-based secret masking in logs, error payloads, and audit trails.
- [x] **Human Approval**: Mandatory approval workflow for destructive and high-risk operations.
- [x] **Execution Budgets**: Bounded steps, timeouts, and tool call counts preventing runaway loops.
