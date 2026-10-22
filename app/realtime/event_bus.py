"""Real-time event schema and central event bus publisher."""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.time import utc_now


class HUDEvent(BaseModel):
    """Normalized real-time HUD event contract."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    timestamp: datetime = Field(default_factory=utc_now)
    task_id: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """Centralized event publisher for asynchronous HUD event distribution."""

    def __init__(self) -> None:
        self._subscribers: set[Any] = set()
        self._history: list[dict[str, Any]] = []
        self._max_history: int = 200

    def register_manager(self, manager: Any) -> None:
        self._subscribers.add(manager)

    def unregister_manager(self, manager: Any) -> None:
        self._subscribers.discard(manager)

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
        correlation_id: str | None = None,
        user_id: str | None = None,
    ) -> HUDEvent:
        """Publish a typed event to all connected HUD subscribers and store in history."""
        # Sanitize sensitive keys from payload
        clean_payload = self._sanitize_payload(payload or {})

        event = HUDEvent(
            type=event_type,
            task_id=task_id,
            correlation_id=correlation_id,
            payload=clean_payload,
        )
        event_dict = event.model_dump(mode="json")

        # Keep in-memory ring buffer for reconnect recovery
        self._history.append(event_dict)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Broadcast to registered managers
        for subscriber in list(self._subscribers):
            try:
                if asyncio.iscoroutinefunction(subscriber.broadcast):
                    await subscriber.broadcast(event_dict, user_id=user_id)
                else:
                    subscriber.broadcast(event_dict, user_id=user_id)
            except Exception as e:
                logger.error(f"Error publishing event {event_type} to subscriber: {e}")

        return event

    def get_recent_events(self, limit: int = 50, since_event_id: str | None = None) -> list[dict[str, Any]]:
        """Retrieve recent events for reconnect recovery."""
        if since_event_id:
            idx = -1
            for i, evt in enumerate(self._history):
                if evt.get("event_id") == since_event_id:
                    idx = i
                    break
            if idx != -1:
                return self._history[idx + 1 : idx + 1 + limit]

        return self._history[-limit:]

    @staticmethod
    def _sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
        """Redact secrets from event payloads."""
        sensitive_keys = {"token", "key", "password", "secret", "api_key", "authorization"}
        cleaned = {}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = EventBus._sanitize_payload(v)
            else:
                cleaned[k] = v
        return cleaned


# Singleton instance
event_bus = EventBus()
