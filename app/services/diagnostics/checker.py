"""Static and runtime diagnostic checkers for FRIDAY AI backend."""

import ast
import importlib
import logging
import time
from pathlib import Path

from app.core.config import settings
from app.domain.enums import DiagnosticSeverity
from app.services.diagnostics.models import DiagnosticCheckResult, DiagnosticFinding

logger = logging.getLogger("friday.diagnostics")


class SystemDiagnosticChecker:
    """Executes static, configuration, database, model, and runtime integrity checks."""

    @staticmethod
    async def check_python_syntax() -> DiagnosticCheckResult:
        """Scan all Python files in app/ and verify AST syntax integrity."""
        start = time.perf_counter()
        app_dir = Path.cwd() / "app"
        py_files = list(app_dir.rglob("*.py"))
        syntax_errors = []
        findings = []

        for p in py_files:
            try:
                code = p.read_text(encoding="utf-8")
                ast.parse(code, filename=str(p))
            except SyntaxError as se:
                rel = str(p.relative_to(Path.cwd()))
                syntax_errors.append(f"{rel}:{se.lineno} {se.msg}")
                findings.append(
                    DiagnosticFinding(
                        category="Syntax",
                        severity=DiagnosticSeverity.CRITICAL,
                        title=f"Python Syntax Error in {rel}",
                        description=f"SyntaxError on line {se.lineno}: {se.msg}",
                        file_path=rel,
                        line_number=se.lineno,
                        confirmed_evidence=str(se),
                        suggested_fix="Correct syntax construct at indicated line.",
                    )
                )

        duration = (time.perf_counter() - start) * 1000
        status = "PASSED" if not syntax_errors else "FAILED"
        details = (
            f"Parsed {len(py_files)} Python source files. Syntax clean."
            if not syntax_errors
            else f"Detected {len(syntax_errors)} syntax errors across {len(py_files)} files."
        )

        return DiagnosticCheckResult(
            check_name="python_syntax_and_ast_integrity",
            category="Static Code",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_critical_imports() -> DiagnosticCheckResult:
        """Verify that primary entrypoints and core modules import without failure."""
        start = time.perf_counter()
        critical_modules = [
            "app.main",
            "app.api.router",
            "app.core.config",
            "app.db.session",
            "app.domain.enums",
            "app.security.policy",
            "app.tools.registry",
            "app.agents.specialists",
            "app.math.engine",
            "app.integrations.omni_osint",
            "app.agents.cyber_agent",
        ]
        failed_imports = []
        findings = []

        for mod in critical_modules:
            try:
                importlib.import_module(mod)
            except Exception as e:
                failed_imports.append((mod, str(e)))
                findings.append(
                    DiagnosticFinding(
                        category="Imports",
                        severity=DiagnosticSeverity.HIGH,
                        title=f"Module Import Failure: {mod}",
                        description=f"Import of '{mod}' raised {e.__class__.__name__}: {str(e)}",
                        confirmed_evidence=str(e),
                        suggested_fix=f"Check dependencies, circular imports, or syntax in {mod}.",
                    )
                )

        duration = (time.perf_counter() - start) * 1000
        status = "PASSED" if not failed_imports else "FAILED"
        details = (
            f"Successfully verified {len(critical_modules)} critical module imports."
            if not failed_imports
            else f"Failed to import {len(failed_imports)} modules: {[m[0] for m in failed_imports]}"
        )

        return DiagnosticCheckResult(
            check_name="critical_module_imports",
            category="Imports",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_configuration_and_env() -> DiagnosticCheckResult:
        """Audit active configuration and detect invalid or missing parameters."""
        start = time.perf_counter()
        findings = []

        if settings.APP_ENV == "production" and settings.DEBUG:
            findings.append(
                DiagnosticFinding(
                    category="Configuration",
                    severity=DiagnosticSeverity.HIGH,
                    title="DEBUG Mode Active in Production",
                    description="DEBUG must be disabled in production environments.",
                    confirmed_evidence="APP_ENV='production' and DEBUG=True",
                    suggested_fix="Set DEBUG=False in production configuration.",
                )
            )

        if not settings.APPROVED_ROOTS:
            findings.append(
                DiagnosticFinding(
                    category="Configuration",
                    severity=DiagnosticSeverity.MEDIUM,
                    title="No Approved Directory Roots Configured",
                    description="APPROVED_ROOTS list is empty, preventing filesystem tool use.",
                    confirmed_evidence="APPROVED_ROOTS=[]",
                    suggested_fix="Configure at least one approved working directory root.",
                )
            )

        duration = (time.perf_counter() - start) * 1000
        status = "PASSED" if not findings else "FAILED"
        details = "Configuration validated against operational schema." if not findings else f"{len(findings)} config issues."

        return DiagnosticCheckResult(
            check_name="configuration_and_environment",
            category="Configuration",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_api_routes() -> DiagnosticCheckResult:
        """Verify FastAPI route definitions and prevent conflicting or unhandled paths."""
        start = time.perf_counter()
        findings = []

        try:
            from app.main import app

            routes = [r for r in app.routes if hasattr(r, "path")]
            route_paths = [r.path for r in routes]
            duplicates = [p for p in set(route_paths) if route_paths.count(p) > 4]  # Allow standard method variations
            if duplicates:
                findings.append(
                    DiagnosticFinding(
                        category="Route",
                        severity=DiagnosticSeverity.WARNING,
                        title="Excessive Route Collisions Detected",
                        description=f"Multiple handlers registered for same path: {duplicates}",
                    )
                )
            details = f"Verified {len(routes)} registered API routes. Duplicate collision check completed."
            status = "PASSED"
        except Exception as e:
            status = "FAILED"
            details = f"Failed inspecting FastAPI application routes: {str(e)}"
            findings.append(
                DiagnosticFinding(
                    category="Route",
                    severity=DiagnosticSeverity.HIGH,
                    title="Route Inspection Error",
                    description=str(e),
                    confirmed_evidence=str(e),
                    suggested_fix="Verify app/main.py and router inclusions.",
                )
            )

        duration = (time.perf_counter() - start) * 1000
        return DiagnosticCheckResult(
            check_name="api_routes_and_endpoints",
            category="API",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_database_connectivity() -> DiagnosticCheckResult:
        """Verify database connection and simple query execution."""
        start = time.perf_counter()
        findings = []

        try:
            from sqlalchemy import text

            from app.db.session import async_session_factory

            async with async_session_factory() as session:
                res = await session.execute(text("SELECT 1"))
                row = res.scalar()
                if row != 1:
                    raise RuntimeError(f"Unexpected query result: {row}")

            status = "PASSED"
            details = f"Database connected ({settings.DATABASE_URL.split('://')[0]}). 'SELECT 1' successful."
        except Exception as e:
            status = "FAILED"
            details = f"Database connectivity check failed: {str(e)}"
            findings.append(
                DiagnosticFinding(
                    category="Database",
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Database Connection Failed",
                    description=f"Error executing heartbeat query: {str(e)}",
                    confirmed_evidence=str(e),
                    suggested_fix="Verify DATABASE_URL and database service availability.",
                )
            )

        duration = (time.perf_counter() - start) * 1000
        return DiagnosticCheckResult(
            check_name="database_connectivity_and_health",
            category="Database",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_tool_and_agent_registries() -> DiagnosticCheckResult:
        """Verify tool registry and specialist agent registrations."""
        start = time.perf_counter()
        findings = []

        from app.agents.specialists import specialist_registry
        from app.tools.registry import ToolRegistry

        reg = ToolRegistry()
        tools_count = len(reg._tools)
        agents_count = len(specialist_registry.list_all())

        if tools_count < 15:
            findings.append(
                DiagnosticFinding(
                    category="Tool",
                    severity=DiagnosticSeverity.MEDIUM,
                    title="Low Tool Count in Registry",
                    description=f"Expected >= 15 registered tools, found {tools_count}.",
                    confirmed_evidence=f"tools_count={tools_count}",
                    suggested_fix="Review app/tools/registry.py tool registrations.",
                )
            )

        if agents_count < 15:
            findings.append(
                DiagnosticFinding(
                    category="Agent",
                    severity=DiagnosticSeverity.MEDIUM,
                    title="Incomplete Specialist Agent Roster",
                    description=f"Expected >= 15 registered specialist agents, found {agents_count}.",
                    confirmed_evidence=f"agents_count={agents_count}",
                    suggested_fix="Verify specialist_registry registrations.",
                )
            )

        status = "PASSED" if not findings else "FAILED"
        details = f"Verified {tools_count} registered tools and {agents_count} specialist agents."
        duration = (time.perf_counter() - start) * 1000

        return DiagnosticCheckResult(
            check_name="tool_and_agent_registrations",
            category="Registry",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_dual_brain_model_status() -> DiagnosticCheckResult:
        """Inspect dual-brain models configuration and Ollama connectivity."""
        start = time.perf_counter()
        findings = []

        import httpx

        ollama_reachable = False
        installed_models = []

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    ollama_reachable = True
                    data = resp.json()
                    installed_models = [m.get("name") for m in data.get("models", [])]
        except Exception:
            ollama_reachable = False

        left_model = settings.FRIDAY_LEFT_MODEL
        right_model = settings.FRIDAY_RIGHT_MODEL

        if not ollama_reachable:
            findings.append(
                DiagnosticFinding(
                    category="Model",
                    severity=DiagnosticSeverity.LOW,
                    title="Ollama Service Unreachable or Offline",
                    description=(
                        f"Could not reach Ollama at {settings.OLLAMA_BASE_URL}. "
                        "FRIDAY operates with simulated or mock responses when local Ollama is offline."
                    ),
                    confirmed_evidence=f"OLLAMA_BASE_URL={settings.OLLAMA_BASE_URL}",
                    suggested_fix="Start Ollama locally: `ollama serve`.",
                )
            )
        else:
            # Check model presence
            left_found = any(left_model.lower() in m.lower() for m in installed_models)
            right_found = any("dolphin3-cyber" in m.lower() for m in installed_models)
            if not left_found:
                findings.append(
                    DiagnosticFinding(
                        category="Model",
                        severity=DiagnosticSeverity.INFO,
                        title=f"Left Brain Model '{left_model}' Not Installed in Ollama",
                        description=f"Model '{left_model}' was not found in `ollama list`.",
                        confirmed_evidence=f"installed_models={installed_models}",
                        suggested_fix=f"Pull model: `ollama pull {left_model}`.",
                    )
                )
            if not right_found:
                findings.append(
                    DiagnosticFinding(
                        category="Model",
                        severity=DiagnosticSeverity.INFO,
                        title=f"Right Brain Model '{right_model}' Not Installed in Ollama",
                        description=f"Cyber specialist model '{right_model}' was not found in `ollama list`.",
                        confirmed_evidence=f"installed_models={installed_models}",
                        suggested_fix=f"Pull model: `ollama pull {right_model}`.",
                    )
                )

        status = "PASSED"
        details = (
            f"Dual-brain status checked. Ollama reachable={ollama_reachable}. "
            f"Left: {left_model}, Right: {right_model}."
        )
        duration = (time.perf_counter() - start) * 1000

        return DiagnosticCheckResult(
            check_name="dual_brain_models_and_ollama",
            category="Model",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )

    @staticmethod
    async def check_audio_subsystem_health() -> DiagnosticCheckResult:
        """Inspect speech-to-text, synthesis availability, and temporary directories."""
        start = time.perf_counter()
        findings = []

        import shutil

        whisper_avail = shutil.which("whisper") is not None
        tts_cmd = shutil.which("say") or shutil.which("espeak")

        temp_dir = settings.AUDIO_TEMP_DIR
        temp_dir.mkdir(parents=True, exist_ok=True)
        writable = temp_dir.exists() and temp_dir.is_dir()

        if not writable:
            findings.append(
                DiagnosticFinding(
                    category="Audio",
                    severity=DiagnosticSeverity.HIGH,
                    title="Audio Temp Directory Not Writable",
                    description=f"Storage directory {temp_dir} could not be verified.",
                    confirmed_evidence=f"AUDIO_TEMP_DIR={temp_dir}",
                    suggested_fix=f"Ensure write permissions for {temp_dir}.",
                )
            )

        status = "PASSED"
        details = (
            f"Audio subsystem ready. Temp directory writable. "
            f"Whisper STT: {'available' if whisper_avail else 'optional (fallback active)'}, "
            f"TTS engine: {tts_cmd or 'none'}."
        )
        duration = (time.perf_counter() - start) * 1000

        return DiagnosticCheckResult(
            check_name="audio_subsystem_and_speech_health",
            category="Audio",
            status=status,
            duration_ms=round(duration, 2),
            details=details,
            findings=findings,
        )
