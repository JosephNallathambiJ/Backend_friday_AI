"""Central AI Activity State Service for the HUD Visualizer.

Maintains truthful agent activity status, step progression, and emits real-time events.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.time import utc_now
from app.realtime.event_bus import event_bus

VALID_ACTIVITY_STATES = {
    "idle",
    "listening",
    "transcribing",
    "thinking",
    "planning",
    "researching",
    "executing_tool",
    "running_terminal",
    "speaking",
    "waiting_for_approval",
    "completed",
    "error",
    "cancelled",
}


class AgentActivityState(BaseModel):
    """Activity state schema for the central HUD visualizer."""

    state: str = "idle"
    task_id: str | None = None
    description: str = "Systems standing by. Ready for tactical command."
    current_step: int = 0
    total_steps: int = 0
    awaiting_approval: bool = False
    last_successful_operation: datetime | None = None
    last_error_category: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class ActivityService:
    """Singleton managing global and per-task AI activity telemetry."""

    _current_state: AgentActivityState = AgentActivityState()

    @classmethod
    def get_state(cls) -> AgentActivityState:
        """Retrieve current visualizer activity state."""
        return cls._current_state

    @classmethod
    async def set_state(
        cls,
        state: str,
        task_id: str | None = None,
        description: str | None = None,
        current_step: int = 0,
        total_steps: int = 0,
        awaiting_approval: bool = False,
        error_category: str | None = None,
    ) -> AgentActivityState:
        """Update activity state and broadcast real-time event to HUD."""
        if state not in VALID_ACTIVITY_STATES:
            state = "idle"

        last_success = cls._current_state.last_successful_operation
        if state == "completed":
            last_success = utc_now()

        default_descriptions = {
            "idle": "Systems standing by. Ready for tactical command.",
            "listening": "Listening for vocal command input...",
            "transcribing": "Transcribing audio input stream...",
            "thinking": "Processing tactical reasoning...",
            "planning": "Decomposing tactical objectives and tool plan...",
            "researching": "Querying knowledge index and web intelligence...",
            "executing_tool": f"Executing tool action (step {current_step}/{total_steps})...",
            "running_terminal": "Executing bounded terminal subprocess...",
            "speaking": "Generating vocal telemetry synthesis...",
            "waiting_for_approval": "Awaiting security approval for privileged action.",
            "completed": "Operation successfully completed.",
            "error": f"Operation error: {error_category or 'execution failure'}",
            "cancelled": "Operation cancelled by user.",
        }

        cls._current_state = AgentActivityState(
            state=state,
            task_id=task_id,
            description=description or default_descriptions.get(state, "Processing..."),
            current_step=current_step,
            total_steps=total_steps,
            awaiting_approval=awaiting_approval,
            last_successful_operation=last_success,
            last_error_category=error_category,
            updated_at=utc_now(),
        )

        # Broadcast mapped event
        event_type = f"agent.{state}" if state not in {"listening", "transcribing", "speaking"} else f"voice.{state}"
        if state == "error":
            event_type = "agent.failed"

        await event_bus.publish(
            event_type=event_type,
            task_id=task_id,
            payload={
                "state": cls._current_state.state,
                "description": cls._current_state.description,
                "current_step": cls._current_state.current_step,
                "total_steps": cls._current_state.total_steps,
                "awaiting_approval": cls._current_state.awaiting_approval,
            },
        )

        return cls._current_state


activity_service = ActivityService()
