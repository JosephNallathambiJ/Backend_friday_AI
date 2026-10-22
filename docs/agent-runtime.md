# Agent Runtime & Execution Lifecycle

## 1. Overview

FRIDAY AI's Agent Runtime provides a resilient, bounded, and auditable execution framework for multi-agent workflows. It coordinates 8 specialist agents, enforces per-run execution budgets, supports cancellation, and integrates with the human approval workflow.

## 2. Logical Multi-Agent Roles

The runtime exposes 8 specialized agent personas:
1. **Orchestrator Agent**: Analyzes the user's intent, creates structured execution plans, checks constraints, and coordinates tool execution.
2. **Research Agent**: Performs internet searches and retrieves public webpages with SSRF defense.
3. **Files Agent**: Performs safe file operations (list, search, read, write with backups, move, copy, and trash deletion).
4. **Browser Agent**: Controls isolated browser sessions for navigation, form filling, and DOM extraction.
5. **Device Agent**: Collects permitted hardware and OS telemetry, dispatches local notifications, and launches permitted apps.
6. **Contacts Agent**: Manages and searches authorized address book records with privacy minimization.
7. **Developer and Command Agent**: Inspects code, inspects Git repositories and diffs, and executes controlled command profiles.
8. **Workflow Agent**: Chains multi-step tools into resumable workflows with automatic retry policies.

## 3. Execution Lifecycle & State Machine

```
   [ PENDING ] ---> Plan Generated
        |
        v
   [ RUNNING ] <---> Executes permitted tools within budget
        |
        +---> Requires Approval ---> [ WAITING_FOR_APPROVAL ]
        |                                    |
        |                             Approved / Rejected
        |                                    v
        |                              [ RUNNING ]
        v
   [ COMPLETED ] / [ FAILED ] / [ CANCELLED ]
```

## 4. Execution Budgets & Safeguards

Every `AgentRun` has an immutable execution budget:
- `max_steps`: Maximum number of plan steps allowed (default: 25).
- `max_duration_seconds`: Timeout limit for entire run (default: 300s).
- `max_tool_calls`: Maximum allowable tool executions (default: 50).
- Immediate cancellation check between steps via `/api/v1/agents/runs/{run_id}/cancel`.

## 5. API Reference

- `POST /api/v1/agents/runs`: Create and execute an agent run.
- `GET /api/v1/agents/runs`: List runs with pagination.
- `GET /api/v1/agents/runs/{run_id}`: Retrieve run status, plan, and current budget.
- `POST /api/v1/agents/runs/{run_id}/cancel`: Cancel an active run.
- `GET /api/v1/agents/runs/{run_id}/events`: Retrieve structured event stream.
