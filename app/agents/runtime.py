"""Agent Runtime managing runs, planning, execution budgets, approvals, and events."""

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planner import Planner
from app.core.exceptions import NotFoundError, SecurityPolicyError
from app.core.time import utc_now
from app.db.models.agent import AgentRun, AgentRunEvent
from app.db.models.approval import ApprovalRequest
from app.domain.enums import AgentRunStatus, AgentType, ApprovalStatus, PolicyOutcome
from app.domain.schemas import AgentRunCreate
from app.security.policy import PolicyEngine
from app.tools.registry import tool_registry


class AgentRuntime:
    """Bounded, durable agent runtime executing plans and tracking progress."""

    @staticmethod
    async def create_run(
        db: AsyncSession,
        run_data: AgentRunCreate,
    ) -> AgentRun:
        """Initialize an agent run, generate a plan, and persist state."""
        agent_type = (
            AgentType(run_data.agent_type)
            if run_data.agent_type in [t.value for t in AgentType]
            else AgentType.ORCHESTRATOR
        )

        plan = Planner.generate_plan(run_data.goal)

        run = AgentRun(
            agent_type=agent_type,
            status=AgentRunStatus.PENDING,
            goal=run_data.goal,
            project_id=run_data.project_id,
            conversation_id=run_data.conversation_id,
            plan_data=plan.model_dump(),
            execution_budget={
                "max_steps": run_data.max_steps,
                "current_step": 0,
                "max_duration_seconds": run_data.max_duration_seconds,
                "max_tool_calls": run_data.max_tool_calls,
                "tool_call_count": 0,
            },
            current_step_index=0,
            cancellation_requested=False,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        # Log initial event
        event = AgentRunEvent(
            run_id=run.id,
            event_type="run_created",
            message=f"Agent run created with goal: {run.goal}",
            payload={"plan": plan.model_dump()},
        )
        db.add(event)
        await db.commit()

        return run

    @staticmethod
    async def execute_run_steps(
        db: AsyncSession,
        run_id: str,
    ) -> AgentRun:
        """Execute remaining plan steps within defined execution budget."""
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        run = (await db.execute(stmt)).scalars().first()
        if not run:
            raise NotFoundError(f"Agent run '{run_id}' not found.")

        if run.cancellation_requested:
            run.status = AgentRunStatus.CANCELLED
            await db.commit()
            return run

        run.status = AgentRunStatus.RUNNING
        await db.commit()

        plan_dict = run.plan_data or {}
        steps = plan_dict.get("steps", [])
        budget = run.execution_budget
        start_time = time.time()

        for idx in range(run.current_step_index, len(steps)):
            # 1. Check Cancellation
            await db.refresh(run)
            if run.cancellation_requested:
                run.status = AgentRunStatus.CANCELLED
                await db.commit()
                return run

            # 2. Check Execution Budget
            if budget["current_step"] >= budget["max_steps"]:
                run.status = AgentRunStatus.FAILED
                run.error_message = f"Exceeded max step budget of {budget['max_steps']} steps."
                await db.commit()
                return run

            if budget["tool_call_count"] >= budget["max_tool_calls"]:
                run.status = AgentRunStatus.FAILED
                run.error_message = (
                    f"Exceeded max tool call budget of {budget['max_tool_calls']} calls."
                )
                await db.commit()
                return run

            if (time.time() - start_time) > budget["max_duration_seconds"]:
                run.status = AgentRunStatus.FAILED
                run.error_message = (
                    f"Exceeded max duration budget of {budget['max_duration_seconds']}s."
                )
                await db.commit()
                return run

            step = steps[idx]
            tool_name = step.get("tool_name")
            tool_params = step.get("tool_parameters", {})

            # Log step start
            db.add(
                AgentRunEvent(
                    run_id=run.id,
                    event_type="step_started",
                    message=f"Starting step {idx + 1}: {step.get('description')}",
                    payload={"step": step},
                )
            )
            await db.commit()

            if tool_name:
                try:
                    tool = tool_registry.get_tool(tool_name)

                    # 3. Policy Engine Evaluation
                    eval_res = await PolicyEngine.evaluate_action(
                        db=db,
                        tool_name=tool_name,
                        risk_level=tool.risk_level,
                        required_capabilities=tool.required_capabilities,
                        parameters=tool_params,
                        requires_approval=tool.requires_approval,
                    )

                    # If action requires approval, create approval request and pause run
                    if eval_res.outcome == PolicyOutcome.REQUIRE_APPROVAL:
                        approval = ApprovalRequest(
                            task_id=run.id,
                            tool_name=tool_name,
                            action_description=step.get("description", f"Execute {tool_name}"),
                            risk_level=tool.risk_level,
                            arguments_redacted=tool_params,
                            status=ApprovalStatus.PENDING,
                            expires_at=utc_now(),
                        )
                        db.add(approval)
                        await db.commit()
                        await db.refresh(approval)

                        run.status = AgentRunStatus.WAITING_FOR_APPROVAL
                        run.current_step_index = idx
                        db.add(
                            AgentRunEvent(
                                run_id=run.id,
                                event_type="approval_required",
                                message=f"Approval required for '{tool_name}' ({eval_res.reason})",
                                payload={"approval_id": approval.id, "tool_name": tool_name},
                            )
                        )
                        await db.commit()
                        return run

                    if eval_res.outcome == PolicyOutcome.DENY:
                        raise SecurityPolicyError(eval_res.reason)

                    # 4. Execute tool
                    tool_res = await tool_registry.execute_tool(
                        name=tool_name,
                        parameters=tool_params,
                        session=db,
                        task_id=run.id,
                    )

                    budget["tool_call_count"] += 1
                    step["status"] = "completed" if tool_res.success else "failed"
                    step["result"] = tool_res.data if tool_res.success else tool_res.error

                    db.add(
                        AgentRunEvent(
                            run_id=run.id,
                            event_type="tool_executed",
                            message=f"Executed tool '{tool_name}' with success={tool_res.success}",
                            payload={"success": tool_res.success, "data": tool_res.data},
                        )
                    )
                except Exception as e:
                    step["status"] = "failed"
                    step["error"] = str(e)
                    run.status = AgentRunStatus.FAILED
                    run.error_message = f"Step {idx + 1} failed: {e}"
                    db.add(
                        AgentRunEvent(
                            run_id=run.id,
                            event_type="step_failed",
                            message=f"Step {idx + 1} failed: {e}",
                            payload={"error": str(e)},
                        )
                    )
                    await db.commit()
                    return run

            budget["current_step"] += 1
            run.current_step_index = idx + 1
            run.execution_budget = budget
            run.plan_data = plan_dict
            await db.commit()

        # All steps completed successfully
        run.status = AgentRunStatus.COMPLETED
        run.result_summary = f"Plan completed successfully with {len(steps)} steps executed."
        db.add(
            AgentRunEvent(
                run_id=run.id,
                event_type="run_completed",
                message=run.result_summary,
                payload={"completed_steps": len(steps)},
            )
        )
        await db.commit()
        return run

    @staticmethod
    async def cancel_run(db: AsyncSession, run_id: str) -> AgentRun:
        """Request cancellation of an active run."""
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        run = (await db.execute(stmt)).scalars().first()
        if not run:
            raise NotFoundError(f"Agent run '{run_id}' not found.")

        run.cancellation_requested = True
        run.status = AgentRunStatus.CANCELLED
        db.add(
            AgentRunEvent(
                run_id=run.id,
                event_type="run_cancelled",
                message="Run cancellation requested by user.",
            )
        )
        await db.commit()
        await db.refresh(run)
        return run

    @staticmethod
    async def list_runs(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[AgentRun]:
        stmt = select(AgentRun).order_by(AgentRun.created_at.desc()).offset(offset).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def get_run(db: AsyncSession, run_id: str) -> AgentRun:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        run = (await db.execute(stmt)).scalars().first()
        if not run:
            raise NotFoundError(f"Agent run '{run_id}' not found.")
        return run

    @staticmethod
    async def get_run_events(db: AsyncSession, run_id: str) -> list[AgentRunEvent]:
        run = await AgentRuntime.get_run(db, run_id)
        stmt = (
            select(AgentRunEvent)
            .where(AgentRunEvent.run_id == run.id)
            .order_by(AgentRunEvent.created_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())
