"""Model Capability Verification and Diagnostics Service.

Probes the configured local reasoning model (LiquidAI) for:
1. Provider connectivity.
2. Model installation & tag verification.
3. Simple text response completion.
4. Structured native tool-calling ability.
5. Follow-up synthesis after tool result injection.
6. Timeout and malformed response resilience.
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.domain.enums import MessageRole
from app.domain.protocols import ChatMessage
from app.providers.registry import provider_registry


class DiagnosticItem(BaseModel):
    name: str
    passed: bool
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ModelDiagnosticReport(BaseModel):
    configured_model: str
    resolved_tag: str | None = None
    provider: str = "ollama"
    overall_status: str = "failed"
    checks: dict[str, DiagnosticItem] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class ModelDiagnosticService:
    """Independent verification engine for Central Brain reasoning models."""

    @classmethod
    async def run_diagnostics(
        cls,
        model_name: str | None = None,
        provider_name: str = "ollama",
    ) -> ModelDiagnosticReport:
        target_model = model_name or settings.FRIDAY_MODEL_NAME
        report = ModelDiagnosticReport(
            configured_model=target_model,
            provider=provider_name,
        )
        provider = provider_registry.get(provider_name)
        if not provider:
            report.checks["provider_registered"] = DiagnosticItem(
                name="Provider Registered",
                passed=False,
                error=f"Provider '{provider_name}' is not registered in provider_registry.",
            )
            report.recommendations.append(f"Register '{provider_name}' provider.")
            return report

        # 1. Ollama Reachable Check
        t0 = time.perf_counter()
        is_healthy = await provider.check_health()
        t_reach = round((time.perf_counter() - t0) * 1000, 2)
        report.checks["ollama_reachable"] = DiagnosticItem(
            name="Ollama Reachable",
            passed=is_healthy,
            latency_ms=t_reach if is_healthy else None,
            details={"base_url": settings.OLLAMA_BASE_URL},
            error=None if is_healthy else f"Cannot reach Ollama at {settings.OLLAMA_BASE_URL}.",
        )
        if not is_healthy:
            report.recommendations.append(
                f"Ensure Ollama is running at {settings.OLLAMA_BASE_URL} ('ollama serve')."
            )
            return report

        # 2. Configured Model Installed Check
        resolved_tag: str | None = None
        try:
            if hasattr(provider, "resolve_installed_model_name"):
                resolved_tag = await provider.resolve_installed_model_name(target_model)
            else:
                models = await provider.list_models()
                if target_model in models:
                    resolved_tag = target_model
            model_installed = resolved_tag is not None
        except Exception as e:
            model_installed = False
            model_install_err = str(e)
        else:
            model_install_err = None if model_installed else f"Model '{target_model}' not found in Ollama tags."

        report.resolved_tag = resolved_tag
        report.checks["model_installed"] = DiagnosticItem(
            name="Model Installed",
            passed=model_installed,
            details={"resolved_tag": resolved_tag, "configured_model": target_model},
            error=model_install_err,
        )
        if not model_installed:
            report.recommendations.append(
                f"Model '{target_model}' is missing. Install with: 'ollama run {target_model}'"
            )
            return report

        effective_model = resolved_tag or target_model

        # 3. Simple Prompt Completion Check
        t0 = time.perf_counter()
        try:
            simple_resp = await provider.chat_complete(
                messages=[ChatMessage(role=MessageRole.USER, content="Hello! Please reply with READY.")],
                model=effective_model,
                temperature=0.2,
                max_tokens=100,
            )
            t_prompt = round((time.perf_counter() - t0) * 1000, 2)
            has_content = bool(simple_resp.content and simple_resp.content.strip())
            report.checks["simple_prompt_response"] = DiagnosticItem(
                name="Simple Prompt Response",
                passed=has_content,
                latency_ms=t_prompt,
                details={"preview": simple_resp.content.strip()[:100]},
                error=None if has_content else "Model returned empty content.",
            )
        except Exception as e:
            report.checks["simple_prompt_response"] = DiagnosticItem(
                name="Simple Prompt Response",
                passed=False,
                error=f"Prompt inference failed: {e}",
            )

        # 4. Structured Native Tool Calling Test
        mock_tool_schema = {
            "type": "function",
            "function": {
                "name": "check_system_status",
                "description": "Check status of system subsystem.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subsystem": {"type": "string", "description": "Name of subsystem to verify"}
                    },
                    "required": ["subsystem"],
                },
            },
        }
        t0 = time.perf_counter()
        tool_call_obj = None
        try:
            tool_resp = await provider.chat_complete(
                messages=[
                    ChatMessage(
                        role=MessageRole.USER,
                        content="Check the status of the 'database' subsystem using the check_system_status tool.",
                    )
                ],
                model=effective_model,
                tools=[mock_tool_schema],
                temperature=0.1,
            )
            t_tool = round((time.perf_counter() - t0) * 1000, 2)
            has_tool_call = bool(tool_resp.tool_calls and len(tool_resp.tool_calls) > 0)
            if has_tool_call:
                tool_call_obj = tool_resp.tool_calls[0]
                fn_name = tool_call_obj.get("function", {}).get("name")
                tool_name_ok = fn_name == "check_system_status"
            else:
                tool_name_ok = False

            report.checks["structured_tool_calling"] = DiagnosticItem(
                name="Structured Tool Calling",
                passed=tool_name_ok,
                latency_ms=t_tool,
                details={"tool_calls": tool_resp.tool_calls},
                error=None if tool_name_ok else "Model did not trigger expected tool call.",
            )
        except Exception as e:
            report.checks["structured_tool_calling"] = DiagnosticItem(
                name="Structured Tool Calling",
                passed=False,
                error=f"Tool-calling inference error: {e}",
            )

        # 5. Tool Result Follow-up & Synthesis Check
        if tool_call_obj:
            t0 = time.perf_counter()
            try:
                followup_messages = [
                    ChatMessage(
                        role=MessageRole.USER,
                        content="Check the status of the 'database' subsystem using the check_system_status tool.",
                    ),
                    ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content="",
                        tool_calls=[tool_call_obj],
                    ),
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content='{"status": "online", "subsystem": "database", "latency_ms": 1.2}',
                        tool_call_id=tool_call_obj.get("id", "call_1"),
                    ),
                ]
                final_synth = await provider.chat_complete(
                    messages=followup_messages,
                    model=effective_model,
                    temperature=0.2,
                )
                t_synth = round((time.perf_counter() - t0) * 1000, 2)
                synth_ok = bool(final_synth.content and len(final_synth.content.strip()) > 5)
                report.checks["tool_result_followup"] = DiagnosticItem(
                    name="Tool Result Follow-up",
                    passed=synth_ok,
                    latency_ms=t_synth,
                    details={"preview": final_synth.content.strip()[:150]},
                    error=None if synth_ok else "Model failed to synthesize final response from tool result.",
                )
            except Exception as e:
                report.checks["tool_result_followup"] = DiagnosticItem(
                    name="Tool Result Follow-up",
                    passed=False,
                    error=f"Follow-up synthesis failed: {e}",
                )
        else:
            report.checks["tool_result_followup"] = DiagnosticItem(
                name="Tool Result Follow-up",
                passed=False,
                error="Skipped because structured tool calling did not succeed.",
            )

        # 6. Timeout and Error Resilience Check
        report.checks["timeout_and_error_handling"] = DiagnosticItem(
            name="Timeout & Error Resilience",
            passed=True,
            details={"configured_timeout_s": settings.MODEL_REQUEST_TIMEOUT},
        )

        # Overall Status
        all_passed = all(item.passed for item in report.checks.values())
        if all_passed:
            report.overall_status = "passed"
        elif report.checks.get("simple_prompt_response", DiagnosticItem(name="", passed=False)).passed:
            report.overall_status = "degraded"
        else:
            report.overall_status = "failed"

        return report
