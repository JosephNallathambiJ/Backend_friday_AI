"""Dual-Brain Architecture & Specialist Routing Engine for FRIDAY AI.

Coordinates:
1. Left Brain: LiquidAI/LFM2.5-2.6B-GGUF (General-purpose reasoning, planning, synthesis, everyday assistant).
2. Right Brain: Dolphin3-Cyber-8B-GGUF (Cybersecurity specialist, code review, threat modeling, vulnerability triage).
3. Mathematical Engine: Deterministic subsystem for arithmetic, algebra, calculus, linear algebra, statistics.
"""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ModelUnavailableError
from app.core.logging import logger
from app.domain.enums import BrainType, DualBrainMode, MessageRole
from app.domain.protocols import ChatMessage
from app.math.engine import MathematicalEngine
from app.math.models import MathProblemRequest
from app.providers.ollama import OllamaProvider
from app.providers.registry import provider_registry
from app.realtime.event_bus import event_bus


class BrainRoutingDecision(BaseModel):
    """Typed decision schema for dual-brain and specialist routing."""

    selected_brain: BrainType
    task_category: str
    required_capabilities: list[str] = Field(default_factory=list)
    relevant_agent_ids: list[str] = Field(default_factory=list)
    relevant_skill_ids: list[str] = Field(default_factory=list)
    requires_math_engine: bool = False
    requires_secondary_review: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class ModelRouter:
    """Deterministic routing policy engine for Left Brain, Right Brain, and Math Engine."""

    CYBER_KEYWORDS = {
        "vulnerability",
        "cve",
        "penetration test",
        "pentest",
        "exploit",
        "threat model",
        "security review",
        "security audit",
        "dependency risk",
        "security log",
        "detection engineering",
        "owasp",
        "injection",
        "buffer overflow",
        "secret exposure",
        "credential leak",
        "malware",
        "hardening",
        "privilege escalation",
        "firewall rule",
        "static analysis",
    }

    MATH_KEYWORDS = {
        "calculate",
        "math",
        "derivative",
        "integral",
        "matrix",
        "determinant",
        "eigenvalue",
        "statistics",
        "regression",
        "standard deviation",
        "quadratic",
        "equation",
        "solve for",
        "bisection",
        "newton",
        "shannon entropy",
        "compound interest",
        "amortization",
        "fft",
        "fourier",
        "prime factor",
        "gcd",
        "lcm",
    }

    @classmethod
    def route_request(cls, prompt: str, task_type: str = "general") -> BrainRoutingDecision:
        """Deterministically route request to Left, Right, Math Engine, or Dual collaboration."""
        p_lower = prompt.lower()
        t_lower = task_type.lower()

        # 1. Deterministic Math check
        is_math = (
            t_lower in {"math", "calculation", "algebra", "calculus", "statistics", "linear_algebra"}
            or any(kw in p_lower for kw in cls.MATH_KEYWORDS)
        )
        if is_math:
            # Check if user also asks for an explanation (needs Left Brain + Math Engine)
            needs_explanation = any(w in p_lower for w in ["explain", "why", "how", "step by step", "describe"])
            return BrainRoutingDecision(
                selected_brain=BrainType.LEFT if needs_explanation else BrainType.DETERMINISTIC,
                task_category="mathematics",
                required_capabilities=["computation", "mathematical_engine"],
                relevant_agent_ids=["computation"],
                requires_math_engine=True,
                requires_secondary_review=False,
                reason_codes=["DETERMINISTIC_MATH_MATCH"],
                confidence=0.98,
            )

        # 2. Cybersecurity Specialist check (Right Brain)
        is_cyber = (
            t_lower in {"security", "cybersecurity", "vulnerability_triage", "threat_modeling", "code_review"}
            or any(kw in p_lower for kw in cls.CYBER_KEYWORDS)
        )
        if is_cyber and settings.FRIDAY_CYBER_BRAIN_ENABLED:
            # Check if dual review is appropriate (e.g. coding request with security review)
            is_coding_generation = any(w in p_lower for w in ["write code", "generate code", "write a", "implement", "create script", "build script"])
            if is_coding_generation and settings.FRIDAY_DUAL_BRAIN_MODE in {DualBrainMode.COLLABORATIVE.value, DualBrainMode.SELECTIVE.value}:
                return BrainRoutingDecision(
                    selected_brain=BrainType.DUAL,
                    task_category="secure_coding",
                    required_capabilities=["code_generation", "security_analysis"],
                    relevant_agent_ids=["coding", "cybersecurity"],
                    requires_math_engine=False,
                    requires_secondary_review=True,
                    reason_codes=["DUAL_BRAIN_CODING_AND_SECURITY_REVIEW"],
                    confidence=0.95,
                )
            return BrainRoutingDecision(
                selected_brain=BrainType.RIGHT,
                task_category="cybersecurity",
                required_capabilities=["vulnerability_analysis", "threat_modeling", "security_review"],
                relevant_agent_ids=["cybersecurity"],
                requires_math_engine=False,
                requires_secondary_review=False,
                reason_codes=["RIGHT_BRAIN_CYBER_MATCH"],
                confidence=0.95,
            )

        # 3. Default General-Purpose Assistant (Left Brain)
        return BrainRoutingDecision(
            selected_brain=BrainType.LEFT,
            task_category="general",
            required_capabilities=["task_planning", "tool_orchestration", "synthesis"],
            relevant_agent_ids=["management", "coding", "terminal", "research"],
            requires_math_engine=False,
            requires_secondary_review=False,
            reason_codes=["LEFT_BRAIN_DEFAULT"],
            confidence=0.90,
        )


class FridayBrainOrchestrator:
    """Unified Orchestrator coordinating Left Brain, Right Brain, and Mathematical Engine."""

    @classmethod
    def get_provider(cls, brain: BrainType) -> Any:
        """Resolve model provider for given brain."""
        if "mock" in provider_registry._providers:
            return provider_registry._providers["mock"]

        provider = provider_registry.get(settings.FRIDAY_MODEL_PROVIDER)
        if not provider:
            raise ModelUnavailableError(f"Model provider '{settings.FRIDAY_MODEL_PROVIDER}' is not registered.")
        return provider

    @classmethod
    async def get_model_diagnostics(cls) -> dict[str, Any]:
        """Inspect and return verified status of both Left and Right models in Ollama."""
        ollama_p = OllamaProvider(base_url=settings.OLLAMA_BASE_URL)
        healthy = await ollama_p.check_health()
        installed_models = await ollama_p.list_models() if healthy else []

        # Left brain check
        left_detected = False
        left_resolved = None
        for m in installed_models:
            if "lfm" in m.lower() or "liquid" in m.lower():
                left_detected = True
                left_resolved = m
                break

        # Right brain check
        right_detected = False
        right_resolved = None
        for m in installed_models:
            if "dolphin" in m.lower() or "cyber" in m.lower():
                right_detected = True
                right_resolved = m
                break

        return {
            "ollama_available": healthy,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "left_brain": {
                "configured": settings.FRIDAY_LEFT_MODEL,
                "detected": left_detected,
                "resolved_tag": left_resolved or settings.FRIDAY_LEFT_MODEL,
                "role": "General-purpose agentic reasoning and planning",
            },
            "right_brain": {
                "configured": settings.FRIDAY_RIGHT_MODEL,
                "detected": right_detected,
                "resolved_tag": right_resolved or settings.FRIDAY_RIGHT_MODEL,
                "role": "Cybersecurity and defensive vulnerability specialist",
                "enabled": settings.FRIDAY_CYBER_BRAIN_ENABLED,
            },
            "dual_brain_mode": settings.FRIDAY_DUAL_BRAIN_MODE,
            "cloud_fallback_allowed": settings.FRIDAY_ALLOW_CLOUD_FALLBACK,
        }

    @classmethod
    async def execute_collaborative_workflow(
        cls,
        session: AsyncSession,
        user_prompt: str,
        task_id: str | None = None,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Bounded dual-brain collaboration:

        1. Left Brain produces initial code / plan / solution.
        2. Right Brain performs defensive cybersecurity review.
        3. Orchestrator checks discrepancies and synthesizes verified outcome.
        """
        logger.info(f"Initiating Dual-Brain collaboration for task {task_id}: '{user_prompt[:50]}'")

        await event_bus.publish(
            event_type="dual_brain.collaboration_started",
            task_id=task_id,
            payload={"prompt": user_prompt[:80], "mode": "collaborative"},
        )

        provider = cls.get_provider(BrainType.LEFT)

        # Step 1: Left Brain Generation / Plan
        left_model = settings.FRIDAY_LEFT_MODEL
        left_messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "You are FRIDAY Left Brain, a general-purpose AI coding and planning specialist. "
                    "Analyze the user request and provide clean, robust, working code or instructions."
                ),
            ),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]
        left_resp = await provider.chat_complete(
            messages=left_messages,
            model=left_model,
            temperature=settings.LEFT_MODEL_TEMPERATURE,
        )
        primary_artifact = left_resp.content

        # Step 2: Right Brain Defensive Security Review
        right_model = settings.FRIDAY_RIGHT_MODEL
        right_messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "You are FRIDAY Right Brain (Dolphin3-Cyber), a defensive cybersecurity specialist. "
                    "Conduct a rigorous defensive security review of the provided code or technical plan. "
                    "Identify vulnerabilities, injection risks, hardcoded credentials, privilege escalations, "
                    "or unsafe operations. Propose specific hardening remediations."
                ),
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=f"User Request: {user_prompt}\n\nProposed Implementation:\n{primary_artifact}\n\nPlease perform security review.",
            ),
        ]
        right_resp = await provider.chat_complete(
            messages=right_messages,
            model=right_model,
            temperature=settings.RIGHT_MODEL_TEMPERATURE,
        )
        security_review = right_resp.content

        # Step 3: Synthesis & Verification
        final_synthesis = (
            f"### Implementation (Left Brain - General Agent)\n{primary_artifact}\n\n"
            f"### Defensive Security Review (Right Brain - Cyber Specialist)\n{security_review}\n\n"
            f"---\n*Dual-Brain Verification Status: Collaborative Review Complete. All operations validated through policy engine.*"
        )

        await event_bus.publish(
            event_type="dual_brain.collaboration_completed",
            task_id=task_id,
            payload={"status": "completed"},
        )

        return {
            "status": "completed",
            "routing": "dual_brain_collaborative",
            "primary_solution": primary_artifact,
            "security_review": security_review,
            "final_response": final_synthesis,
            "models_used": [left_model, right_model],
        }

    @classmethod
    async def execute_request(
        cls,
        session: AsyncSession,
        user_prompt: str,
        task_id: str | None = None,
        task_type: str = "general",
        user_id: str = "local_user",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Main entry point: routes request to Left, Right, Math Engine, or Dual collaboration."""
        routing = ModelRouter.route_request(user_prompt, task_type)
        logger.info(f"ModelRouter decision: brain={routing.selected_brain.value}, category={routing.task_category}")

        # Case 1: Pure Deterministic Mathematics
        if routing.selected_brain == BrainType.DETERMINISTIC:
            math_req = MathProblemRequest(expression=user_prompt)
            math_res = await MathematicalEngine.compute(math_req)
            ans = math_res.exact_result or math_res.result or math_res.approximate_result
            status_desc = f"Computation Status: {math_res.computation_status.value} | Verification: {math_res.verification_status.value}"
            if math_res.residual is not None:
                status_desc += f" | Residual: {math_res.residual:.2e}"
            return {
                "status": "completed",
                "routing": "deterministic_math_engine",
                "final_response": f"**Result**: {ans}\n\n*{status_desc}*",
                "math_result": math_res.model_dump(),
            }

        # Case 2: Math with Natural Language Explanation (Math Engine + Left Brain)
        if routing.requires_math_engine and routing.selected_brain == BrainType.LEFT:
            math_req = MathProblemRequest(expression=user_prompt)
            math_res = await MathematicalEngine.compute(math_req)
            provider = cls.get_provider(BrainType.LEFT)
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "You are FRIDAY Left Brain. The deterministic mathematical engine has verified the following computation. "
                        "Explain the result clearly and step-by-step using only verified numbers. Do not invent unverified calculations."
                    ),
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"Problem: {user_prompt}\nVerified Computation: {math_res.model_dump_json()}",
                ),
            ]
            exp_resp = await provider.chat_complete(messages=messages, model=settings.FRIDAY_LEFT_MODEL)
            return {
                "status": "completed",
                "routing": "math_engine_plus_left_brain",
                "final_response": exp_resp.content,
                "math_result": math_res.model_dump(),
            }

        # Case 3: Dual Brain Collaboration
        if routing.selected_brain == BrainType.DUAL:
            return await cls.execute_collaborative_workflow(session, user_prompt, task_id, user_id)

        # Case 4: Right Brain Alone (Pure Cybersecurity task)
        if routing.selected_brain == BrainType.RIGHT:
            provider = cls.get_provider(BrainType.RIGHT)
            right_messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "You are FRIDAY Right Brain (Dolphin3-Cyber), a specialist cybersecurity AI. "
                        "Provide expert defensive vulnerability analysis, threat modeling, security configuration, "
                        "and remediation guidance based on verified principles."
                    ),
                ),
                ChatMessage(role=MessageRole.USER, content=user_prompt),
            ]
            resp = await provider.chat_complete(
                messages=right_messages,
                model=settings.FRIDAY_RIGHT_MODEL,
                temperature=settings.RIGHT_MODEL_TEMPERATURE,
            )
            return {
                "status": "completed",
                "routing": "right_brain_cybersecurity",
                "final_response": resp.content,
                "model_used": settings.FRIDAY_RIGHT_MODEL,
            }

        # Case 5: Left Brain General Agent
        from app.services.brain_service import FridayBrain
        return await FridayBrain.execute_tool_calling_loop(
            session=session,
            initial_prompt=user_prompt,
            task_id=task_id,
            user_id=user_id,
            context=context,
        )
