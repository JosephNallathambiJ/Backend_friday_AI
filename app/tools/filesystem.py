"""Filesystem tools with strict path validation."""

import os
import time
from pathlib import Path
from typing import Any

from app.domain.enums import ToolRiskLevel
from app.security.path_validation import validate_path_in_roots
from app.tools.base import BaseTool, ToolResult


class ListFilesTool(BaseTool):
    name = "list_files"
    description = "List files and directories within an approved project root."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "subpath": {"type": "string", "default": ""},
            "recursive": {"type": "boolean", "default": False},
        },
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        subpath = parameters.get("subpath", "")
        recursive = parameters.get("recursive", False)

        try:
            target = validate_path_in_roots(subpath if subpath else Path.cwd())
            if not target.exists():
                return ToolResult(success=False, error=f"Path '{target}' does not exist.")

            entries: list[dict[str, Any]] = []
            if recursive:
                # Bounded walk
                count = 0
                for root, dirs, files in os.walk(target):
                    dirs[:] = [
                        d
                        for d in dirs
                        if not d.startswith(".") and d != "node_modules" and d != "__pycache__"
                    ]
                    for f in files:
                        if f.startswith("."):
                            continue
                        p = Path(root) / f
                        entries.append(
                            {
                                "path": str(p.relative_to(target)),
                                "is_dir": False,
                                "size": p.stat().st_size,
                            }
                        )
                        count += 1
                        if count >= 200:
                            break
                    if count >= 200:
                        break
            else:
                for item in target.iterdir():
                    if item.name.startswith("."):
                        continue
                    entries.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "is_dir": item.is_dir(),
                            "size": item.stat().st_size if item.is_file() else 0,
                        }
                    )

            elapsed = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=True,
                data={"entries": entries, "count": len(entries)},
                execution_time_ms=elapsed,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a text file inside an approved project root."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "max_lines": {"type": "integer", "default": 500},
        },
        "required": ["file_path"],
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        file_path_str = parameters.get("file_path")
        max_lines = parameters.get("max_lines", 500)

        if not file_path_str:
            return ToolResult(success=False, error="file_path parameter is required.")

        try:
            target = validate_path_in_roots(file_path_str)
            if not target.exists() or not target.is_file():
                return ToolResult(
                    success=False, error=f"File '{target}' does not exist or is not a regular file."
                )

            # Check file size limit (5MB max)
            if target.stat().st_size > 5 * 1024 * 1024:
                return ToolResult(success=False, error="File exceeds 5MB limit.")

            # Read safely as text
            with open(target, encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)

            elapsed = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=True,
                data={
                    "file_path": str(target),
                    "content": content,
                    "lines_read": len(lines),
                },
                execution_time_ms=elapsed,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
