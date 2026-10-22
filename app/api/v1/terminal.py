"""Controlled Terminal Sessions and Execution endpoints."""

import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.db.session import async_session_factory
from app.domain.schemas import APIResponse
from app.services.terminal_session_service import TerminalSessionService

router = APIRouter(prefix="/terminal", tags=["Terminal Panel Backend"])


class CreateSessionRequest(BaseModel):
    working_directory: str | None = Field(default=None, description="Permitted working directory path")
    profile_name: str = Field(default="system_check", description="Execution profile: system_check, git_inspect, python_test, code_lint")


class ExecuteCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Explicit terminal command line string")


@router.post("/sessions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_terminal_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Create a new bounded terminal session."""
    session_obj = await TerminalSessionService.create_session(
        session=db,
        user_id=user_id,
        working_directory=payload.working_directory,
        profile_name=payload.profile_name,
    )
    return APIResponse(
        success=True,
        data={
            "session_id": session_obj.id,
            "user_id": session_obj.user_id,
            "working_directory": session_obj.working_directory,
            "profile_name": session_obj.profile_name,
            "is_active": session_obj.is_active,
            "created_at": session_obj.created_at.isoformat(),
        },
    )


@router.get("/sessions/{session_id}", response_model=APIResponse)
async def get_terminal_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Retrieve details and status of a terminal session."""
    session_obj = await TerminalSessionService.get_session(db, session_id)
    return APIResponse(
        success=True,
        data={
            "session_id": session_obj.id,
            "user_id": session_obj.user_id,
            "working_directory": session_obj.working_directory,
            "profile_name": session_obj.profile_name,
            "is_active": session_obj.is_active,
            "created_at": session_obj.created_at.isoformat(),
        },
    )


@router.post("/sessions/{session_id}/commands", response_model=APIResponse)
async def execute_terminal_command(
    session_id: str,
    payload: ExecuteCommandRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Execute an explicit allowlisted command in the specified session."""
    result = await TerminalSessionService.execute_command(
        session=db,
        session_id=session_id,
        command_line=payload.command,
        user_id=user_id,
    )
    return APIResponse(success=True, data=result)


@router.get("/sessions/{session_id}/history", response_model=APIResponse)
async def get_session_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Retrieve executed command history and outputs for the session."""
    history = await TerminalSessionService.get_history(
        session=db,
        session_id=session_id,
        limit=limit,
        user_id=user_id,
    )
    return APIResponse(success=True, data=history)


@router.post("/sessions/{session_id}/cancel", response_model=APIResponse)
@router.post("/sessions/{session_id}/interrupt", response_model=APIResponse)
async def cancel_session_command(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Cancel or interrupt currently executing process in the terminal session."""
    res = await TerminalSessionService.cancel_active_command(
        session=db,
        session_id=session_id,
        user_id=user_id,
    )
    return APIResponse(success=True, data=res)


@router.delete("/sessions/{session_id}", response_model=APIResponse)
async def delete_terminal_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Deactivate and close a terminal session."""
    res = await TerminalSessionService.close_session(
        session=db,
        session_id=session_id,
        user_id=user_id,
    )
    return APIResponse(success=True, data=res)


@router.websocket("/sessions/{session_id}/stream")
async def terminal_session_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),
):
    """Live interactive WebSocket stream for the HUD Linux terminal panel.
    
    Streams MOTD, stdout, stderr, process completion exit codes, and supports live commands.
    """
    await websocket.accept()

    async with async_session_factory() as db:
        try:
            session_obj = await TerminalSessionService.get_session(db, session_id)
        except Exception as e:
            await websocket.send_json({
                "event": "terminal.error",
                "session_id": session_id,
                "detail": f"Terminal session not found or inactive: {e}",
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # Send initial MOTD & session connection metadata
    await websocket.send_json({
        "event": "terminal.connected",
        "session_id": session_id,
        "motd": TerminalSessionService.get_terminal_motd(),
        "working_directory": session_obj.working_directory,
        "profile_name": session_obj.profile_name,
        "user": session_obj.user_id,
    })

    try:
        while True:
            message = await websocket.receive()
            cmd_text = ""
            action = ""

            if "text" in message and message["text"]:
                raw_text = message["text"].strip()
                try:
                    payload = json.loads(raw_text)
                    if isinstance(payload, dict):
                        action = payload.get("action", "")
                        cmd_text = payload.get("command", "") or payload.get("input", "")
                    else:
                        cmd_text = str(payload)
                except Exception:
                    cmd_text = raw_text

            if action in {"interrupt", "cancel"}:
                async with async_session_factory() as db:
                    cancel_res = await TerminalSessionService.cancel_active_command(
                        session=db, session_id=session_id
                    )
                await websocket.send_json({
                    "event": "terminal.interrupted",
                    "session_id": session_id,
                    "result": cancel_res,
                })
                continue

            if cmd_text:
                async with async_session_factory() as db:
                    try:
                        res = await TerminalSessionService.execute_command(
                            session=db,
                            session_id=session_id,
                            command_line=cmd_text,
                        )
                    except Exception as cmd_err:
                        err_text = str(cmd_err)
                        if "sudo" in cmd_text or "su" in cmd_text:
                            err_msg = "sudo: elevation to root requires administrative policy authorization and is locked in standard HUD session.\n"
                        else:
                            err_msg = f"{cmd_text}: command rejected by security policy: {err_text}\n"

                        res = {
                            "stdout": "",
                            "stderr": err_msg,
                            "exit_code": 1,
                            "execution_time_ms": 5,
                        }

                # Send structured execution output and exit events
                await websocket.send_json({
                    "event": "terminal.output",
                    "session_id": session_id,
                    "command": cmd_text,
                    "stdout": res["stdout"],
                    "stderr": res["stderr"],
                    "exit_code": res["exit_code"],
                    "execution_time_ms": res["execution_time_ms"],
                })
                await websocket.send_json({
                    "event": "terminal.exit",
                    "session_id": session_id,
                    "exit_code": res["exit_code"],
                })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({
                "event": "terminal.error",
                "session_id": session_id,
                "detail": str(exc),
            })
            await websocket.close()
        except Exception:
            pass

