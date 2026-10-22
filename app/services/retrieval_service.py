"""Retrieval and full-text search indexing service using SQLite FTS5."""

import hashlib
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.document import DocumentChunk, DocumentIndex
from app.db.models.project import Project
from app.security.path_validation import is_sensitive_path, validate_path_in_roots


class RetrievalService:
    @staticmethod
    def _chunk_text(text_content: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
        """Split text content into overlapping chunks."""
        chunks = []
        start = 0
        text_len = len(text_content)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text_content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start += chunk_size - overlap
        return chunks

    @staticmethod
    async def index_project_files(
        session: AsyncSession,
        project_id: str,
    ) -> dict[str, Any]:
        """Index all eligible project files into SQLite tables and FTS5 index."""
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if not project:
            raise NotFoundError(f"Project '{project_id}' not found.")

        root = validate_path_in_roots(project.root_path)

        # Clear existing indexes for this project
        old_indexes = (
            (
                await session.execute(
                    select(DocumentIndex).where(DocumentIndex.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
        for doc in old_indexes:
            await session.delete(doc)

        await session.execute(
            text("DELETE FROM document_fts WHERE project_id = :project_id"),
            {"project_id": project_id},
        )
        await session.flush()

        indexed_files = 0
        total_chunks = 0

        for dirpath, dirnames, filenames in os.walk(root):
            # Exclude vendor, cache, and hidden directories
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in {"node_modules", ".venv", "__pycache__", "build", "dist"}
            ]

            for filename in filenames:
                if filename.startswith("."):
                    continue
                file_path = Path(dirpath) / filename
                if is_sensitive_path(file_path):
                    continue

                # Only index text/code files
                if file_path.suffix.lower() not in {
                    ".py",
                    ".md",
                    ".txt",
                    ".json",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".sh",
                    ".sql",
                }:
                    continue

                if file_path.stat().st_size > 2 * 1024 * 1024:
                    continue  # Skip > 2MB

                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                doc = DocumentIndex(
                    project_id=project_id,
                    file_path=str(file_path.relative_to(root)),
                    content_hash=content_hash,
                    file_size_bytes=len(content.encode("utf-8")),
                    mime_type="text/plain",
                )
                session.add(doc)
                await session.flush()

                chunks = RetrievalService._chunk_text(content)
                for idx, chunk_content in enumerate(chunks):
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        content=chunk_content,
                        token_count=len(chunk_content.split()),
                    )
                    session.add(chunk)
                    await session.flush()

                    # Add to FTS5 virtual table
                    await session.execute(
                        text(
                            """
                            INSERT INTO document_fts (chunk_id, project_id, file_path, content)
                            VALUES (:chunk_id, :project_id, :file_path, :content)
                            """
                        ),
                        {
                            "chunk_id": chunk.id,
                            "project_id": project_id,
                            "file_path": doc.file_path,
                            "content": chunk_content,
                        },
                    )
                    total_chunks += 1

                indexed_files += 1

        await session.commit()
        return {
            "project_id": project_id,
            "files_indexed": indexed_files,
            "total_chunks": total_chunks,
        }

    @staticmethod
    async def search(
        session: AsyncSession,
        query: str,
        project_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        import re

        words = re.findall(r"\w+", query)
        if not words:
            return []
        sanitized = " ".join(f'"{w}"' for w in words)

        sql = """
            SELECT chunk_id, project_id, file_path,
                   snippet(document_fts, 3, '<b>', '</b>', '...', 20) as snippet,
                   content
            FROM document_fts
            WHERE document_fts MATCH :query
        """
        params: dict[str, Any] = {"query": sanitized, "limit": limit}
        if project_id:
            sql += " AND project_id = :project_id"
            params["project_id"] = project_id

        sql += " LIMIT :limit"

        res = await session.execute(text(sql), params)
        rows = res.fetchall()

        return [
            {
                "chunk_id": r[0],
                "project_id": r[1],
                "file_path": r[2],
                "snippet": r[3],
                "content": r[4],
            }
            for r in rows
        ]
