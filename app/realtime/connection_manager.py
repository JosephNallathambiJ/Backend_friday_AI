"""WebSocket Connection Manager for Tactical HUD Real-Time Events."""

import asyncio
from typing import Any

from starlette.websockets import WebSocket, WebSocketState

from app.core.logging import logger
from app.realtime.event_bus import event_bus


class ConnectionManager:
    """Manages active WebSocket connections for the HUD frontend."""

    def __init__(self) -> None:
        # Maps connection_id -> (WebSocket, user_id)
        self.active_connections: dict[str, tuple[WebSocket, str]] = {}
        self._lock = asyncio.Lock()
        # Register with event_bus
        event_bus.register_manager(self)

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str = "local_user") -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[connection_id] = (websocket, user_id)
        logger.info(f"HUD WebSocket connected: {connection_id} (user: {user_id})")

    async def disconnect(self, connection_id: str) -> None:
        """Unregister a disconnected WebSocket connection."""
        async with self._lock:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
        logger.info(f"HUD WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, message: dict[str, Any], connection_id: str) -> None:
        """Send message directly to a specific connection."""
        async with self._lock:
            conn_data = self.active_connections.get(connection_id)
            if not conn_data:
                return
            ws, _ = conn_data

        if ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to connection {connection_id}: {e}")

    async def broadcast(self, message: dict[str, Any], user_id: str | None = None) -> None:
        """Broadcast message to all connected clients or filtered by user_id."""
        async with self._lock:
            targets = list(self.active_connections.items())

        for conn_id, (ws, conn_user) in targets:
            if user_id and conn_user != user_id:
                continue
            if ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Error broadcasting to {conn_id}: {e}")

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


connection_manager = ConnectionManager()
