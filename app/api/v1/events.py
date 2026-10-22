"""Real-time HUD WebSocket events route and history inspection."""

import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from app.core.config import settings
from app.core.logging import logger
from app.domain.schemas import APIResponse
from app.realtime.connection_manager import connection_manager
from app.realtime.event_bus import event_bus
from app.services.activity_service import activity_service

router = APIRouter(prefix="/events", tags=["Real-time HUD Events"])


@router.websocket("")
async def hud_events_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    user_id: str = Query(default="local_user"),
    since_event_id: str | None = Query(default=None),
):
    """Real-time bidirectional WebSocket event stream for the tactical HUD."""
    # Verify token if API_KEY is set
    if settings.API_KEY and token != settings.API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    connection_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, connection_id=connection_id, user_id=user_id)

    try:
        # 1. Send initial connection greeting with current agent visualizer state
        initial_state = activity_service.get_state()
        await websocket.send_json({
            "event_id": str(uuid.uuid4()),
            "type": "system.connected",
            "payload": {
                "connection_id": connection_id,
                "user_id": user_id,
                "agent_state": initial_state.model_dump(mode="json"),
            },
        })

        # 2. Replay buffered events if since_event_id provided (reconnect recovery)
        if since_event_id:
            missed_events = event_bus.get_recent_events(limit=50, since_event_id=since_event_id)
            for evt in missed_events:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(evt)

        # 3. Message loop (handle client ping / messages)
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": data.get("timestamp")})
            elif msg_type == "get_state":
                curr_state = activity_service.get_state()
                await websocket.send_json({
                    "event_id": str(uuid.uuid4()),
                    "type": f"agent.{curr_state.state}",
                    "payload": curr_state.model_dump(mode="json"),
                })

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id)
    except Exception as e:
        logger.warning(f"WebSocket error on connection {connection_id}: {e}")
        await connection_manager.disconnect(connection_id)


@router.get("/history", response_model=APIResponse)
async def get_recent_event_history(
    limit: int = Query(default=50, ge=1, le=100),
    since_event_id: str | None = Query(default=None),
):
    """Inspect buffered in-memory HUD event history for recovery or debugging."""
    events = event_bus.get_recent_events(limit=limit, since_event_id=since_event_id)
    return APIResponse(success=True, data={"count": len(events), "events": events})
