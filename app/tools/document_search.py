"""Document full-text search tool using SQLite FTS5."""

import time
from typing import Any

from sqlalchemy import text

from app.db.session import async_session_factory
from app.domain.enums import ToolRiskLevel
from app.tools.base import BaseTool, ToolResult


class SearchProjectFilesTool(BaseTool):
    name = "search_project_files"
    description = "Search indexed project files and documents using SQLite FTS5 full-text matching."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "project_id": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        query = parameters.get("query", "").strip()
        project_id = parameters.get("project_id")
        limit = parameters.get("limit", 5)

        if not query:
            return ToolResult(success=False, error="Query parameter is required.")

        # Sanitize query for FTS5 (avoid syntax error on hyphens or special characters)
        import re

        words = re.findall(r"\w+", query)
        if not words:
            return ToolResult(success=True, data={"results": []})
        sanitized_query = " ".join(f'"{w}"' for w in words)

        try:
            async with async_session_factory() as session:
                sql = """
                    SELECT chunk_id, file_path, snippet(document_fts, 3, '<b>', '</b>', '...', 15) as snippet, content
                    FROM document_fts
                    WHERE document_fts MATCH :query
                """
                params: dict[str, Any] = {"query": sanitized_query, "limit": limit}
                if project_id:
                    sql += " AND project_id = :project_id"
                    params["project_id"] = project_id

                sql += " LIMIT :limit"

                res = await session.execute(text(sql), params)
                rows = res.fetchall()

                results = [
                    {
                        "chunk_id": row[0],
                        "file_path": row[1],
                        "snippet": row[2],
                        "content_preview": row[3][:200] if row[3] else "",
                    }
                    for row in rows
                ]

                elapsed = int((time.time() - start_time) * 1000)
                return ToolResult(
                    success=True,
                    data={"results": results, "count": len(results)},
                    execution_time_ms=elapsed,
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
