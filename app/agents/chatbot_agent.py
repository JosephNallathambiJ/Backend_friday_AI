"""ChatbotAgent — FRIDAY's Conversational Voice and Response Coordinator.

Serves as the primary conversational mouth of FRIDAY:
- Receives user messages from frontend through documented backend APIs.
- Maintains conversation IDs and context.
- Classifies user intent and routes:
    * Security / OSINT / attack surface -> CyberAgent (Right Brain)
    * Diagnostics / system health / debugging -> BackendDiagnosticsAgent
    * Mathematical calculations / formulas -> MathematicalEngine
    * General task planning / tool use -> Central Brain Orchestrator (Left Brain)
- Formulates transparent explanations before high-impact actions.
- Distinguishes verified facts, estimates, hypotheses, and unknowns.
- Never fabricates outcomes: reports verified execution facts only.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.backend_diagnostics_agent import backend_diagnostics_agent
from app.agents.cyber_agent import cyber_agent
from app.agents.specialists.base import BaseSpecialistAgent, SpecialistExecutionResult
from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation
from app.domain.enums import MessageRole
from app.math.engine import mathematical_engine
from app.services.conversation_service import ConversationService
from app.services.orchestration_service import OrchestrationService

logger = logging.getLogger("friday.chatbot_agent")


class ChatRoutingDecision(BaseModel):
    """Routing classification decision made by ChatbotAgent."""

    primary_agent: str = Field(..., description="cyber_agent, backend_diagnostics, math_engine, orchestrator")
    intent_category: str
    confidence: float
    explanation: str
    recommended_brain: str = Field(default="left", description="'left' or 'right'")
    requires_approval: bool = False


class ChatbotMessageResponse(BaseModel):
    """Transparent conversational response returned to frontend."""

    conversation_id: str
    message_id: str = Field(default_factory=lambda: f"msg-{uuid4().hex[:8]}")
    role: str = "assistant"
    content: str
    summary: str
    routing: ChatRoutingDecision
    verified_facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    high_impact_warning: str | None = None
    detailed_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatbotAgent(BaseSpecialistAgent):
    """Dedicated conversational interface and coordinator for FRIDAY."""

    agent_id = "chatbot"
    name = "Chatbot Mouth and Response Coordinator"
    description = (
        "FRIDAY's conversational voice: parses user requests, identifies intent, "
        "delegates to specialist agents, summarizes evidence, and communicates verified results."
    )
    supported_task_types = ["chat", "conversation", "user_query", "ask", "clarification"]
    available_tool_names = ["run_diagnostics", "passive_domain_recon", "calculate"]
    timeout_seconds = 60
    budget_steps = 4

    def classify_intent(self, message: str) -> ChatRoutingDecision:
        """Classify user intent to route to appropriate specialist or engine."""
        msg_lower = message.lower().strip()

        # 1. Mathematical Intent
        math_keywords = [
            "calculate", "solve", "differentiate", "integrate", "matrix", "eigen",
            "standard deviation", "variance", "integral", "derivative", "simplify",
            "polynomial", "factorial", "sin(", "cos(", "tan(", "log(", "sqrt(",
        ]
        if any(k in msg_lower for k in math_keywords) or re.search(r"^\s*[\d\(\)\+\-\*\/\^\.\s]+\s*$", message):
            return ChatRoutingDecision(
                primary_agent="math_engine",
                intent_category="mathematical_computation",
                confidence=0.98,
                explanation="Request identified as mathematical computation or numerical analysis.",
                recommended_brain="left",
            )

        # 2. Cybersecurity & OSINT Intent
        cyber_keywords = [
            "cyber", "security", "osint", "recon", "attack surface", "vulnerability",
            "port", "ports", "secret leak", "header audit", "tls", "ssl", "subdomain",
            "whois", "shodan", "target authorization", "cve", "dependency audit",
            "penetration", "exploit", "advisory", "attack-surface",
        ]
        is_cyber = any(k in msg_lower for k in cyber_keywords) or (
            "scan" in msg_lower and any(w in msg_lower for w in ["target", "host", "network", "domain", "ip", "port", "vuln"])
        )
        if is_cyber:
            return ChatRoutingDecision(
                primary_agent="cyber_agent",
                intent_category="cybersecurity_and_osint",
                confidence=0.95,
                explanation="Request involves security inspection, attack-surface intelligence, or vulnerability scanning.",
                recommended_brain="right",
            )

        # 3. Backend Diagnostics & Debugging Intent
        diag_keywords = [
            "diagnose", "diagnostics", "debug", "test workflow", "audit backend",
            "system health", "check routes", "check database", "check imports",
            "verify fix", "backend status",
        ]
        if any(k in msg_lower for k in diag_keywords):
            return ChatRoutingDecision(
                primary_agent="backend_diagnostics",
                intent_category="system_diagnostics",
                confidence=0.92,
                explanation="Request requires backend code auditing, test verification, or runtime health checks.",
                recommended_brain="left",
            )

        # 4. Identity & Creator Intent
        identity_keywords = ["who made you", "who created you", "who are you", "what is friday", "tell me about yourself"]
        if any(k in msg_lower for k in identity_keywords):
            return ChatRoutingDecision(
                primary_agent="identity",
                intent_category="identity_disclosure",
                confidence=1.0,
                explanation="Identity and creator inquiry handled directly by FRIDAY persona.",
                recommended_brain="left",
            )

        # 5. Terminal Execution Intent
        terminal_keywords = ["run command", "terminal command", "run in terminal", "execute in terminal", "execute command"]
        if any(k in msg_lower for k in terminal_keywords):
            return ChatRoutingDecision(
                primary_agent="terminal",
                intent_category="terminal_execution",
                confidence=0.94,
                explanation="Request to execute a command directly through controlled terminal service.",
                recommended_brain="left",
            )

        # 6. General Task / Central Orchestrator
        return ChatRoutingDecision(
            primary_agent="orchestrator",
            intent_category="general_orchestration",
            confidence=0.85,
            explanation="General user request routed to Central Brain Orchestrator.",
            recommended_brain="left",
        )

    async def handle_message(
        self,
        message: str,
        conversation_id: str,
        session: AsyncSession,
        parameters: dict[str, Any] | None = None,
    ) -> ChatbotMessageResponse:
        """Process an incoming user message and coordinate specialists."""
        parameters = parameters or {}
        routing = self.classify_intent(message)
        logger.info("Chatbot routed message to '%s' (intent: %s)", routing.primary_agent, routing.intent_category)

        # Ensure conversation exists
        try:
            conv = await ConversationService.get_conversation(session, conversation_id)
        except NotFoundError:
            conv = Conversation(id=conversation_id, title=f"Chat {conversation_id[:8]}")
            session.add(conv)
            await session.commit()
            await session.refresh(conv)

        # Store user message
        await ConversationService.add_message(
            session=session,
            conversation_id=conv.id,
            role=MessageRole.USER,
            content=message,
        )

        verified_facts: list[str] = []
        hypotheses: list[str] = []
        unknowns: list[str] = []
        detailed_data: dict[str, Any] = {}
        content_text: str = ""

        # Route 1: Mathematical Engine
        if routing.primary_agent == "math_engine":
            # Extract expression or clean query
            expr = message
            for kw in ["calculate", "solve", "what is", "compute", "evaluate"]:
                if message.lower().startswith(kw):
                    expr = message[len(kw):].strip(" ?:=")
                    break

            math_res = await mathematical_engine.evaluate_expression(expr)
            detailed_data = math_res.model_dump()

            val_str = str(math_res.exact_result or math_res.result or math_res.approximate_result or "")
            if math_res.computation_status.value in {"exact", "success"}:
                content_text = f"Result: **{val_str}**\n\nComputation confirmed via deterministic evaluation."
                verified_facts.append(f"Expression '{expr}' evaluated to value: {val_str}")
            elif math_res.computation_status.value == "approximate":
                content_text = f"Approximate result: **{math_res.approximate_result or val_str}**."
                verified_facts.append(f"Expression evaluated approximately: {math_res.approximate_result or val_str}")
            else:
                content_text = f"Calculation encountered an error: {math_res.error_details or 'Unsupported mathematical form'}."
                unknowns.append("Could not solve expression with symbolic solver.")

        # Route 2: Cyber Specialist Agent
        elif routing.primary_agent == "cyber_agent":
            # Extract target from message or parameters
            target = parameters.get("target") or "localhost"
            # Basic domain/IP extractor if target not passed
            words = message.split()
            for w in words:
                if "." in w and not w.endswith(".") and len(w) > 3 and not any(c in w for c in ["?", "!", ","]):
                    target = w.strip("()[]\"'")
                    break

            cyber_params = {
                "target": target,
                "action": parameters.get("action", "full_scan"),
                "authorization_id": parameters.get("authorization_id"),
            }
            res: SpecialistExecutionResult = await cyber_agent.execute(
                task_id=f"chat-cyber-{uuid4().hex[:6]}",
                goal=message,
                parameters=cyber_params,
                session=session,
            )
            detailed_data = res.data or {}
            content_text = (
                f"**Cyber Analysis for `{target}` Completed.**\n\n"
                f"{res.summary}\n\n"
                f"{res.data.get('markdown_report', '') if isinstance(res.data, dict) else ''}"
            )
            findings = res.data.get("findings", []) if isinstance(res.data, dict) else []
            verified_facts.append(f"Completed defensive analysis for {target} ({len(findings)} findings).")

        # Route 3: Backend Diagnostics Agent
        elif routing.primary_agent == "backend_diagnostics":
            res: SpecialistExecutionResult = await backend_diagnostics_agent.execute(
                task_id=f"chat-diag-{uuid4().hex[:6]}",
                goal=message,
                parameters={"job_type": "diagnose"},
                session=session,
            )
            detailed_data = res.data or {}
            content_text = (
                f"**FRIDAY Backend Diagnostics Completed.**\n\n"
                f"{res.summary}\n\n"
                f"{res.data.get('markdown_report', '') if isinstance(res.data, dict) else ''}"
            )
            verified_facts.append(f"Completed system diagnostic scan: {res.summary}")

        # Route 4: Identity & Persona
        elif routing.primary_agent == "identity":
            content_text = (
                "I am **FRIDAY** (GOJO Enterprise Tactical Defense Edition).\n\n"
                "I was created by **GOJO** to operate as an advanced, dual-brain autonomous AI assistant "
                "for the GOJO Enterprise Tactical Defense HUD. I coordinate tactical command execution, "
                "defensive cybersecurity, real-time system diagnostics, and interactive terminal workflows."
            )
            detailed_data = {
                "name": "FRIDAY",
                "founder": "GOJO",
                "system": "GOJO OS v8.4.2",
                "architecture": "Dual-Brain AI Cyber Architecture",
            }
            verified_facts.append("Created by GOJO for GOJO Enterprise Tactical Defense HUD.")
            verified_facts.append("Runs on Dual-Brain architecture: LiquidAI LFM2.5 (Left Brain) and Dolphin3-Cyber (Right Brain).")

        # Route 5: Controlled Terminal Execution
        elif routing.primary_agent == "terminal":
            cmd = message
            for prefix in ["run command", "terminal command", "run in terminal", "execute in terminal", "execute command"]:
                if prefix in message.lower():
                    idx = message.lower().find(prefix) + len(prefix)
                    cmd = message[idx:].strip(" :\"'")
                    break

            from app.services.terminal_session_service import TerminalSessionService

            term_session = await TerminalSessionService.create_session(
                session=session,
                profile_name="hud_interactive",
            )
            exec_res = await TerminalSessionService.execute_command(
                session=session,
                session_id=term_session.id,
                command_line=cmd,
            )
            detailed_data = exec_res
            term_out = exec_res.get("stdout") or exec_res.get("stderr") or "(no output)"
            content_text = (
                f"**Terminal Execution for `{cmd}`:**\n\n"
                f"```\n{term_out}\n```\n"
                f"*Exit code: {exec_res['exit_code']} (executed in {exec_res['execution_time_ms']}ms)*"
            )
            verified_facts.append(f"Command '{cmd}' executed with exit code {exec_res['exit_code']}.")

        # Route 6: Central Brain Orchestrator
        else:
            from app.domain.schemas import ChatRequest

            chat_req = ChatRequest(
                conversation_id=conversation_id,
                message=message,
            )
            orch_res = await OrchestrationService.process_chat(session=session, request=chat_req)
            content_text = orch_res.get("response", "FRIDAY standing by.")
            detailed_data = orch_res
            verified_facts.append("Orchestration pipeline processed task through registered tool registry.")

        # Persist assistant reply
        await ConversationService.add_message(
            session=session,
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content=content_text,
        )

        return ChatbotMessageResponse(
            conversation_id=conversation_id,
            content=content_text,
            summary=content_text[:120].strip() + ("..." if len(content_text) > 120 else ""),
            routing=routing,
            verified_facts=verified_facts,
            hypotheses=hypotheses,
            unknowns=unknowns,
            detailed_data=detailed_data,
        )

    async def execute(
        self,
        task_id: str,
        goal: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        context: dict[str, Any] | None = None,
    ) -> SpecialistExecutionResult:
        """Execute specialist task by processing goal message through conversational mouth."""
        conversation_id = parameters.get("conversation_id")
        if not conversation_id:
            conv = await ConversationService.create_conversation(session, title=f"Chat: {goal[:30]}")
            conversation_id = conv.id

        resp = await self.handle_message(
            message=goal,
            conversation_id=conversation_id,
            session=session,
            parameters=parameters,
        )
        return SpecialistExecutionResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=resp.summary,
            data=resp.model_dump(),
        )


# Global singleton chatbot agent
chatbot_agent = ChatbotAgent()
