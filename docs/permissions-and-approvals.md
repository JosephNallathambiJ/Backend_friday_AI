# Permissions, Capabilities & Human Approvals

## 1. Capability Permission Model

FRIDAY AI implements an explicit, independently grantable capability model. The LLM is never the authority that grants its own permissions.

### System Capabilities
- `system.info.read`: Read basic hardware and OS telemetry.
- `filesystem.read`: Enumerate and read files inside approved roots.
- `filesystem.write`: Write, copy, and move files inside approved roots.
- `filesystem.delete`: Move permitted files to recoverable trash.
- `process.execute`: Run permitted development and inspection commands.
- `browser.navigate`: Open public URLs in an isolated browser.
- `browser.read`: Extract visible text and links from web sessions.
- `browser.interact`: Fill and interact with web forms.
- `contacts.read`: Search and view authorized address book entries.
- `contacts.write`: Create, edit, and delete contacts.
- `notifications.send`: Trigger desktop notifications.
- `applications.launch`: Launch permitted local applications.
- `network.fetch`: Perform HTTP requests to public web endpoints.
- `scheduled_tasks.manage`: Schedule background cron or interval jobs.

## 2. Policy Outcomes

When an action is evaluated by the `PolicyEngine` (`app/security/policy.py`), it yields one of three outcomes:
1. `ALLOW`: Safe action within granted capabilities and permitted resource scope.
2. `REQUIRE_APPROVAL`: Consequential, high-impact, or destructive action requiring explicit confirmation.
3. `DENY`: Missing required capability, path traversal attempt, prohibited command, or private network SSRF attempt.

## 3. Human Approval Workflow

When an action requires approval:
1. An immutable `ApprovalRequest` record is created in SQLite with the exact proposed tool parameters.
2. The agent run enters the `WAITING_FOR_APPROVAL` state.
3. The user inspects pending approvals via `GET /api/v1/approvals`.
4. The user makes a decision via:
   - `POST /api/v1/approvals/{id}/approve`
   - `POST /api/v1/approvals/{id}/reject`
5. Upon approval, the action is revalidated and marked `EXECUTED` race-safely, resuming the agent workflow.

## 4. Capability Management APIs

- `GET /api/v1/capabilities`: Inspect all system capabilities, active status, and scopes.
- `POST /api/v1/capabilities/grant`: Grant a capability for a global or scoped resource.
- `POST /api/v1/capabilities/revoke`: Revoke an active capability immediately.
