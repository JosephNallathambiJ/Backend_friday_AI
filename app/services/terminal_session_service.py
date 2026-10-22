"""Terminal Session Management and Controlled Execution Service."""

import asyncio
import os
import shlex
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, SecurityPolicyError, ValidationError
from app.core.logging import logger
from app.db.models.terminal import TerminalCommandHistory, TerminalSession
from app.realtime.event_bus import event_bus
from app.services.activity_service import activity_service
from app.services.command_runner import (
    COMMAND_PROFILES,
    CommandRunnerService,
)


class TerminalSessionService:
    """Manages isolated, audited terminal sessions for the HUD terminal panel."""

    _active_processes: dict[str, asyncio.subprocess.Process] = {}

    @classmethod
    async def create_session(
        cls,
        session: AsyncSession,
        user_id: str = "local_user",
        working_directory: str | None = None,
        profile_name: str = "system_check",
    ) -> TerminalSession:
        """Create a new controlled terminal session bounded to an approved directory and profile."""
        work_dir = working_directory or settings.APPROVED_ROOTS[0]
        work_dir = os.path.abspath(work_dir)

        # Validate directory is within approved roots
        is_approved = any(
            os.path.commonpath([work_dir, os.path.abspath(root)]) == os.path.abspath(root)
            for root in settings.APPROVED_ROOTS
        )
        if not is_approved:
            raise SecurityPolicyError(
                f"Directory '{work_dir}' is not within approved filesystem roots: {settings.APPROVED_ROOTS}"
            )

        if profile_name not in COMMAND_PROFILES:
            profile_name = "system_check"

        term_session = TerminalSession(
            user_id=user_id,
            working_directory=work_dir,
            profile_name=profile_name,
            is_active=True,
        )
        session.add(term_session)
        await session.commit()
        await session.refresh(term_session)

        # Broadcast event
        await event_bus.publish(
            event_type="terminal.session_created",
            user_id=user_id,
            payload={
                "session_id": term_session.id,
                "working_directory": term_session.working_directory,
                "profile_name": term_session.profile_name,
            },
        )

        return term_session

    @classmethod
    async def get_session(cls, session: AsyncSession, session_id: str) -> TerminalSession:
        """Retrieve session or raise NotFoundError."""
        res = await session.execute(
            select(TerminalSession).where(TerminalSession.id == session_id)
        )
        term_session = res.scalar_one_or_none()
        if not term_session:
            raise NotFoundError(f"Terminal session '{session_id}' not found.")
        return term_session

    @classmethod
    async def execute_command(
        cls,
        session: AsyncSession,
        session_id: str,
        command_line: str,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Validate and execute an explicit command within the session's approved profile."""
        term_session = await cls.get_session(session, session_id)
        if not term_session.is_active:
            raise ValidationError(f"Terminal session '{session_id}' is terminated.")

        if term_session.user_id != user_id:
            raise SecurityPolicyError("Unauthorized access to terminal session.")

        command_line = command_line.strip()
        if not command_line:
            raise ValidationError("Command line cannot be empty.")

        # Parse command safely into executable and args
        try:
            tokens = shlex.split(command_line)
        except ValueError as e:
            raise ValidationError(f"Invalid shell command syntax: {e}")

        if not tokens:
            raise ValidationError("Empty command tokens.")

        executable = tokens[0]
        args = tokens[1:]

        # Publish started event and set visualizer activity state
        await event_bus.publish(
            event_type="terminal.command_started",
            user_id=user_id,
            payload={
                "session_id": session_id,
                "executable": executable,
                "args": args,
                "command_line": command_line,
            },
        )
        await activity_service.set_state(
            state="running_terminal",
            description=f"Terminal executing: {executable} {' '.join(args)}",
        )

        # Run controlled command
        result = await CommandRunnerService.run_command(
            executable=executable,
            args=args,
            cwd=term_session.working_directory,
            profile_name=term_session.profile_name,
        )

        # Record in history
        history_entry = TerminalCommandHistory(
            session_id=session_id,
            command_line=command_line,
            executable=executable,
            args=args,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time_ms=result.execution_time_ms,
            timed_out=result.timed_out,
            cancelled=result.cancelled,
        )
        session.add(history_entry)
        await session.commit()
        await session.refresh(history_entry)

        # Broadcast output and completion events
        await event_bus.publish(
            event_type="terminal.command_output",
            user_id=user_id,
            payload={
                "session_id": session_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        await event_bus.publish(
            event_type="terminal.command_completed",
            user_id=user_id,
            payload={
                "session_id": session_id,
                "exit_code": result.exit_code,
                "execution_time_ms": result.execution_time_ms,
                "timed_out": result.timed_out,
            },
        )

        await activity_service.set_state(
            state="idle",
            description="Terminal command completed. Systems standing by.",
        )

        return {
            "id": history_entry.id,
            "session_id": session_id,
            "command_line": command_line,
            "executable": executable,
            "args": args,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_ms": result.execution_time_ms,
            "timed_out": result.timed_out,
            "cancelled": result.cancelled,
            "created_at": history_entry.created_at.isoformat(),
        }

    @classmethod
    async def get_history(
        cls,
        session: AsyncSession,
        session_id: str,
        limit: int = 50,
        user_id: str = "local_user",
    ) -> list[dict[str, Any]]:
        """Retrieve recent command history for session."""
        term_session = await cls.get_session(session, session_id)
        if term_session.user_id != user_id:
            raise SecurityPolicyError("Unauthorized access to terminal session.")

        stmt = (
            select(TerminalCommandHistory)
            .where(TerminalCommandHistory.session_id == session_id)
            .order_by(desc(TerminalCommandHistory.created_at))
            .limit(limit)
        )
        res = await session.execute(stmt)
        entries = res.scalars().all()

        return [
            {
                "id": e.id,
                "session_id": e.session_id,
                "command_line": e.command_line,
                "executable": e.executable,
                "args": e.args,
                "exit_code": e.exit_code,
                "stdout": e.stdout,
                "stderr": e.stderr,
                "execution_time_ms": e.execution_time_ms,
                "timed_out": e.timed_out,
                "cancelled": e.cancelled,
                "created_at": e.created_at.isoformat(),
            }
            for e in reversed(entries)
        ]

    @classmethod
    async def cancel_active_command(
        cls,
        session: AsyncSession,
        session_id: str,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Cancel any running command for this session."""
        term_session = await cls.get_session(session, session_id)
        if term_session.user_id != user_id:
            raise SecurityPolicyError("Unauthorized access to terminal session.")

        proc = cls._active_processes.get(session_id)
        if proc:
            try:
                proc.kill()
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to kill proc for session {session_id}: {e}")
            del cls._active_processes[session_id]

        await activity_service.set_state(
            state="cancelled",
            description=f"Terminal command cancelled in session {session_id}.",
        )
        return {"session_id": session_id, "cancelled": True}

    @classmethod
    async def close_session(
        cls,
        session: AsyncSession,
        session_id: str,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Terminate and deactivate a terminal session."""
        term_session = await cls.get_session(session, session_id)
        if term_session.user_id != user_id:
            raise SecurityPolicyError("Unauthorized access to terminal session.")

        term_session.is_active = False
        await session.commit()
        return {"session_id": session_id, "active": False, "closed": True}

    @classmethod
    async def interrupt_session(
        cls,
        session: AsyncSession,
        session_id: str,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Interrupt and cancel any running command in session (alias for cancellation)."""
        return await cls.cancel_active_command(session=session, session_id=session_id, user_id=user_id)

    @classmethod
    def get_terminal_motd(cls) -> str:
        """Return Linux MOTD banner matching HUD terminal interface."""
        return (
            "Linux fridey-os 6.8.0-gojo-arm64 #1 SMP GNU/Linux\n"
            "GOJO OS v8.4.2 (Gojo Enterprise Edition)\n"
            "* Host:      Gojo Technologies Hub\n"
            "* User:      gojo (UID: 1000 • Standard User Session)\n"
            "* Founder:   GOJO\n"
            "* Terminal:  bash 5.1.26 / zsh 5.9 (xterm-256color)\n"
            "Type 'help' for linux commands, or 'sudo su' to elevate to root.\n"
        )
