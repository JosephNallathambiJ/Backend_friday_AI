"""Filesystem service for safe, scoped file operations.

Implements directory listing, search, atomic writing, backups, copying, moving,
and recoverable trash deletion with project boundary validation.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.exceptions import SecurityPolicyError, ValidationError
from app.security.path_validation import validate_path_in_roots

# Trash directory location within workspace or temporary folder
TRASH_DIR = Path.cwd() / ".friday_trash"


class FilesystemService:
    """Safe, scoped filesystem operations bounded by approved project roots."""

    @staticmethod
    def list_directory(
        directory_path: str = "", recursive: bool = False, max_entries: int = 100
    ) -> dict[str, Any]:
        """List files and directories within an approved root."""
        target = validate_path_in_roots(directory_path if directory_path else Path.cwd())
        if not target.exists() or not target.is_dir():
            raise ValidationError(f"Directory '{target}' does not exist or is not a directory.")

        entries = []
        if recursive:
            count = 0
            for root, dirs, files in os.walk(target):
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "__pycache__", ".venv", ".friday_trash"]
                ]
                for f in files:
                    if f.startswith("."):
                        continue
                    p = Path(root) / f
                    entries.append(
                        {
                            "name": f,
                            "path": str(p.relative_to(target)),
                            "is_dir": False,
                            "size": p.stat().st_size,
                        }
                    )
                    count += 1
                    if count >= max_entries:
                        break
                if count >= max_entries:
                    break
        else:
            for item in target.iterdir():
                if item.name.startswith(".") or item.name == ".friday_trash":
                    continue
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else 0,
                    }
                )

        return {"directory": str(target), "entries": entries, "count": len(entries)}

    @staticmethod
    def search_files(
        query: str, root_path: str = "", max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Search for files by filename pattern within permitted roots."""
        target = validate_path_in_roots(root_path if root_path else Path.cwd())
        results = []
        query_lower = query.lower()

        for root, dirs, files in os.walk(target):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["node_modules", "__pycache__", ".venv"]
            ]
            for f in files:
                if query_lower in f.lower():
                    p = Path(root) / f
                    results.append(
                        {
                            "name": f,
                            "path": str(p),
                            "relative_path": str(p.relative_to(target)),
                            "size": p.stat().st_size,
                        }
                    )
                    if len(results) >= max_results:
                        return results
        return results

    @staticmethod
    def get_file_metadata(file_path: str) -> dict[str, Any]:
        """Retrieve file metadata without loading file content."""
        target = validate_path_in_roots(file_path)
        if not target.exists():
            raise ValidationError(f"File '{target}' does not exist.")

        stat = target.stat()
        return {
            "path": str(target),
            "name": target.name,
            "is_dir": target.is_dir(),
            "size_bytes": stat.st_size,
            "modified_timestamp": stat.st_mtime,
            "extension": target.suffix,
        }

    @staticmethod
    def read_text_file(file_path: str, max_lines: int = 500) -> dict[str, Any]:
        """Read lines from a permitted text file with size limit."""
        target = validate_path_in_roots(file_path)
        if not target.exists() or not target.is_file():
            raise ValidationError(f"Path '{target}' is not a readable file.")

        if target.stat().st_size > 10 * 1024 * 1024:
            raise ValidationError("File exceeds 10MB safety limit.")

        with open(target, encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]

        return {
            "path": str(target),
            "content": "".join(lines),
            "lines_read": len(lines),
            "total_size": target.stat().st_size,
        }

    @staticmethod
    def write_file(
        file_path: str, content: str, create_backup: bool = True, dry_run: bool = False
    ) -> dict[str, Any]:
        """Write content to a file atomically, creating a backup if it already exists."""
        target = validate_path_in_roots(file_path)

        if dry_run:
            return {
                "dry_run": True,
                "target_path": str(target),
                "bytes_to_write": len(content.encode("utf-8")),
                "file_exists": target.exists(),
            }

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        if target.exists() and create_backup:
            backup_path = target.with_suffix(f"{target.suffix}.bak.{int(time.time())}")
            shutil.copy2(target, backup_path)

        # Atomic write: write to temp file in same directory then rename
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            dir=target.parent,
            delete=False,
            encoding="utf-8",
        )
        try:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            os.replace(temp_file.name, target)
        except Exception as e:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise SecurityPolicyError(f"Atomic file write failed: {e}")

        return {
            "success": True,
            "path": str(target),
            "bytes_written": len(content.encode("utf-8")),
            "backup_created": str(backup_path) if backup_path else None,
        }

    @staticmethod
    def copy_file(source_path: str, destination_path: str, dry_run: bool = False) -> dict[str, Any]:
        """Copy a file within permitted roots."""
        src = validate_path_in_roots(source_path)
        dst = validate_path_in_roots(destination_path)

        if not src.exists() or not src.is_file():
            raise ValidationError(f"Source file '{src}' does not exist.")

        if dry_run:
            return {"dry_run": True, "source": str(src), "destination": str(dst)}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"success": True, "source": str(src), "destination": str(dst)}

    @staticmethod
    def move_file(source_path: str, destination_path: str, dry_run: bool = False) -> dict[str, Any]:
        """Move or rename a file within permitted roots."""
        src = validate_path_in_roots(source_path)
        dst = validate_path_in_roots(destination_path)

        if not src.exists():
            raise ValidationError(f"Source file '{src}' does not exist.")

        if dry_run:
            return {"dry_run": True, "source": str(src), "destination": str(dst)}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return {"success": True, "source": str(src), "destination": str(dst)}

    @staticmethod
    def delete_file_to_trash(file_path: str, dry_run: bool = False) -> dict[str, Any]:
        """Move a file to the recoverable trash directory instead of permanent deletion."""
        target = validate_path_in_roots(file_path)
        if not target.exists():
            raise ValidationError(f"File '{target}' does not exist.")

        if dry_run:
            return {
                "dry_run": True,
                "target_path": str(target),
                "action": "move_to_trash",
                "trash_destination": str(TRASH_DIR / target.name),
            }

        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        trash_name = f"{target.name}.deleted.{timestamp}"
        trash_dest = TRASH_DIR / trash_name

        shutil.move(target, trash_dest)
        return {
            "success": True,
            "original_path": str(target),
            "trash_path": str(trash_dest),
            "recoverable": True,
        }
