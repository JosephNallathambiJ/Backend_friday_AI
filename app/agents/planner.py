"""Structured Planner for FRIDAY AI.

Converts natural-language requests into structured, validated execution plans
with goals, constraints, missing information, and discrete plan steps.
"""

from typing import Any

from app.domain.schemas import ExecutionPlan, PlanStep
from app.tools.registry import tool_registry


class Planner:
    """Generates structured plans and maps goals to registered tool actions."""

    @staticmethod
    def generate_plan(goal: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        """Create a structured execution plan for a given user goal."""
        goal_lower = goal.lower()
        steps: list[PlanStep] = []
        constraints: list[str] = [
            "Must operate strictly inside approved project roots or public web destinations",
            "Destructive actions and elevated commands require explicit human approval",
        ]
        missing_info: list[str] = []

        # 1. Web research / browsing intent
        if (
            "http://" in goal_lower
            or "https://" in goal_lower
            or any(
                w in goal_lower
                for w in ["search for", "find on web", "browse", "website", "url", "lookup"]
            )
        ):
            if "http://" in goal or "https://" in goal:
                # Direct URL navigation
                import re

                urls = re.findall(r"https?://\S+", goal)
                url = urls[0] if urls else "https://example.com"
                steps.append(
                    PlanStep(
                        step_id="step_1",
                        description=f"Fetch and extract webpage content from {url}",
                        tool_name="fetch_webpage",
                        tool_parameters={"url": url},
                        required_capabilities=["network.fetch"],
                        requires_approval=False,
                    )
                )
            else:
                steps.append(
                    PlanStep(
                        step_id="step_1",
                        description=f"Search web sources for: {goal}",
                        tool_name="web_search",
                        tool_parameters={"query": goal, "max_results": 5},
                        required_capabilities=["network.fetch"],
                        requires_approval=False,
                    )
                )

        # 2. Filesystem search / read intent
        elif any(
            w in goal_lower
            for w in ["read file", "inspect file", "view file", "cat ", "show me file"]
        ):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="Read specified file inside approved project root",
                    tool_name="read_file",
                    tool_parameters={
                        "file_path": context.get("file_path", "README.md")
                        if context
                        else "README.md"
                    },
                    required_capabilities=["filesystem.read"],
                    requires_approval=False,
                )
            )

        # 3. File search / directory listing intent
        elif any(
            w in goal_lower for w in ["list files", "find files", "explore directory", "tree", "ls"]
        ):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="List project directory contents",
                    tool_name="list_files",
                    tool_parameters={"subpath": "", "recursive": False},
                    required_capabilities=["filesystem.read"],
                    requires_approval=False,
                )
            )

        # 4. Contacts intent
        elif any(w in goal_lower for w in ["contact", "phone number", "email address", "people"]):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="Search authorized device contacts",
                    tool_name="search_contacts",
                    tool_parameters={
                        "query": goal.replace("find contact", "")
                        .replace("search contact", "")
                        .strip()
                    },
                    required_capabilities=["contacts.read"],
                    requires_approval=False,
                )
            )

        # 5. Device telemetry / system info
        elif any(
            w in goal_lower
            for w in ["system info", "device status", "os version", "specs", "cpu count"]
        ):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="Retrieve system telemetry and supported adapters",
                    tool_name="get_system_info",
                    tool_parameters={},
                    required_capabilities=["system.info.read"],
                    requires_approval=False,
                )
            )

        # 6. Git / Developer intent
        elif any(w in goal_lower for w in ["git status", "git diff", "repo status", "branch"]):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="Inspect Git repository status",
                    tool_name="git_status",
                    tool_parameters={"repo_path": "."},
                    required_capabilities=["filesystem.read"],
                    requires_approval=False,
                )
            )

        # Default fallback: inspect directory and status
        else:
            steps.append(
                PlanStep(
                    step_id="step_1",
                    description="Inspect project environment and discover relevant context",
                    tool_name="list_files",
                    tool_parameters={"subpath": "", "recursive": False},
                    required_capabilities=["filesystem.read"],
                    requires_approval=False,
                )
            )

        # Validate proposed tool names against tool_registry
        for step in steps:
            if step.tool_name:
                try:
                    tool = tool_registry.get_tool(step.tool_name)
                    step.required_capabilities = tool.required_capabilities
                    step.requires_approval = tool.requires_approval
                except Exception:
                    missing_info.append(f"Tool '{step.tool_name}' is not registered.")

        return ExecutionPlan(
            goal=goal,
            constraints=constraints,
            missing_information=missing_info,
            steps=steps,
            estimated_duration_seconds=30 * len(steps),
        )
