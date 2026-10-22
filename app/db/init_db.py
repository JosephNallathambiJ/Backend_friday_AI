"""Database schema initialization and FTS5 full-text search table creation."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.base import Base
from app.db.models.tool import ToolDefinition
from app.db.session import engine
from app.domain.enums import ToolRiskLevel


async def init_database():
    """Create all tables and FTS5 virtual table."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # Create standard tables
        await conn.run_sync(Base.metadata.create_all)

        # Create SQLite FTS5 virtual table for document chunks full-text search
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
                    chunk_id UNINDEXED,
                    project_id UNINDEXED,
                    file_path,
                    content,
                    tokenize = 'porter unicode61'
                );
                """
            )
        )
    logger.info("Database tables and FTS5 index initialized successfully.")


async def seed_default_tools(session: AsyncSession):
    """Register core tool definitions in the database."""
    default_tools = [
        ToolDefinition(
            name="list_files",
            description="List files in an approved project directory.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "subpath": {"type": "string", "default": ""},
                    "recursive": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolDefinition(
            name="read_file",
            description="Read the text content of a file within an approved project root.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "max_lines": {"type": "integer", "default": 500},
                },
                "required": ["file_path"],
            },
        ),
        ToolDefinition(
            name="search_project_files",
            description="Perform full-text search across indexed project documents using FTS5.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="git_status",
            description="Check the current Git repository status and branch.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                },
            },
        ),
        ToolDefinition(
            name="git_diff",
            description="Inspect git diff of unstaged or staged changes.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "cached": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolDefinition(
            name="run_terminal_command",
            description="Run an authorized non-destructive command (e.g. pytest, ruff). Consequential commands require human approval.",
            risk_level=ToolRiskLevel.LOCAL_MUTATION,
            requires_approval=True,
            parameters_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "cwd": {"type": "string"},
                },
                "required": ["command"],
            },
        ),
        ToolDefinition(
            name="security_scan",
            description="Perform static security analysis and secret scanning on project files.",
            risk_level=ToolRiskLevel.READ_ONLY,
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                },
            },
        ),
    ]

    for tool in default_tools:
        result = await session.execute(
            select(ToolDefinition).where(ToolDefinition.name == tool.name)
        )
        if not result.scalars().first():
            session.add(tool)

    await session.commit()
