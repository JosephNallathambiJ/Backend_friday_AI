"""Tactical Command Execution Service for HUD."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import AgentRuntime
from app.core.logging import logger
from app.domain.enums import AgentType
from app.domain.schemas import AgentRunCreate
from app.realtime.event_bus import event_bus
from app.services.activity_service import activity_service
from app.services.conversation_service import ConversationService
from app.services.task_service import TaskService


class CommandService:
    """Orchestrates tactical commands submitted from the HUD interface."""

    _idempotency_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    async def process_command(
        cls,
        session: AsyncSession,
        command_text: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
        response_mode: str = "sync",
        locale: str = "en-US",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Process user command text, produce plan, execute authorized tools, and broadcast events."""
        # Check idempotency
        if request_id and request_id in cls._idempotency_cache:
            return cls._idempotency_cache[request_id]

        command_id = str(uuid.uuid4())

        # Ensure conversation exists or create default
        if conversation_id:
            try:
                await ConversationService.get_conversation(session, conversation_id)
            except Exception:
                conv = await ConversationService.create_conversation(
                    session=session, title=f"HUD Command: {command_text[:30]}"
                )
                conversation_id = conv.id
        else:
            conv = await ConversationService.create_conversation(
                session=session, title=f"HUD Command: {command_text[:30]}"
            )
            conversation_id = conv.id

        # Create Task
        task = await TaskService.create_task(
            session=session,
            task_type="hud_command",
            summary=command_text[:100],
            parameters={"command": command_text, "context": context or {}, "locale": locale},
        )
        task_id = task.id

        # Publish command.accepted event
        await event_bus.publish(
            event_type="command.accepted",
            task_id=task_id,
            correlation_id=request_id,
            payload={
                "command_id": command_id,
                "command_text": command_text,
                "status": "accepted",
                "conversation_id": conversation_id,
            },
        )

        # Set HUD activity state to planning
        await activity_service.set_state(
            state="planning",
            task_id=task_id,
            description=f"Formulating tactical plan for: '{command_text[:50]}'",
        )

        # Create AgentRun
        run_in = AgentRunCreate(
            agent_type=AgentType.ORCHESTRATOR,
            goal=command_text,
            conversation_id=conversation_id,
            execution_budget=10,
        )
        run = await AgentRuntime.create_run(session, run_in)
        run_id = run.id

        initial_ack = f"Tactical command accepted. Run {run_id} initiated."

        if response_mode == "async":
            # Return accepted state immediately for asynchronous polling/streaming
            response_payload = {
                "command_id": command_id,
                "task_id": task_id,
                "run_id": run_id,
                "status": "accepted",
                "acknowledgment": initial_ack,
                "approval_required": False,
                "event_ref": f"/api/v1/events?task_id={task_id}",
                "result": None,
            }
            if request_id:
                cls._idempotency_cache[request_id] = response_payload
            return response_payload

        # Sync mode: execute run steps
        await activity_service.set_state(
            state="executing_tool",
            task_id=task_id,
            description=f"Executing tactical plan for '{command_text[:40]}'",
            current_step=1,
            total_steps=len(run.plan_data.get("steps", [])),
        )

        try:
            executed_run = await AgentRuntime.execute_run_steps(session, run.id)
            final_status = executed_run.status.value if hasattr(executed_run.status, "value") else str(executed_run.status)

            approval_required = final_status == "waiting_for_approval"

            if approval_required:
                await activity_service.set_state(
                    state="waiting_for_approval",
                    task_id=task_id,
                    description="Security policy requires user confirmation for privileged action.",
                    awaiting_approval=True,
                )
                await event_bus.publish(
                    event_type="approval.required",
                    task_id=task_id,
                    payload={"run_id": run_id, "summary": "Tool execution requires confirmation."},
                )
            elif final_status == "completed":
                await activity_service.set_state(
                    state="completed",
                    task_id=task_id,
                    description=executed_run.result_summary or "Operation complete.",
                )
                await event_bus.publish(
                    event_type="command.completed",
                    task_id=task_id,
                    payload={"run_id": run_id, "result": executed_run.result_summary},
                )
            else:
                await activity_service.set_state(
                    state="error",
                    task_id=task_id,
                    error_category=executed_run.error_message,
                )
                await event_bus.publish(
                    event_type="command.failed",
                    task_id=task_id,
                    payload={"run_id": run_id, "error": executed_run.error_message},
                )

            response_payload = {
                "command_id": command_id,
                "task_id": task_id,
                "run_id": run_id,
                "status": final_status,
                "acknowledgment": initial_ack,
                "approval_required": approval_required,
                "event_ref": f"/api/v1/events?task_id={task_id}",
                "result": {
                    "summary": executed_run.result_summary,
                    "plan": executed_run.plan_data,
                    "error": executed_run.error_message,
                },
            }

            if request_id:
                cls._idempotency_cache[request_id] = response_payload

            return response_payload

        except Exception as e:
            logger.error(f"Error executing tactical command: {e}")
            await activity_service.set_state(state="error", task_id=task_id, error_category=str(e))
            await event_bus.publish(
                event_type="command.failed",
                task_id=task_id,
                payload={"run_id": run_id, "error": str(e)},
            )
            return {
                "command_id": command_id,
                "task_id": task_id,
                "run_id": run_id,
                "status": "failed",
                "acknowledgment": initial_ack,
                "approval_required": False,
                "event_ref": f"/api/v1/events?task_id={task_id}",
                "result": {"error": str(e)},
            }
