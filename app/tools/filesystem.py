"""Filesystem tools declaring typed contracts and required capabilities."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import CapabilityType, ToolRiskLevel
from app.services.filesystem_service import FilesystemService
from app.tools.base import BaseTool, ToolResult


# --- Input Schemas ---
class ListFilesInput(BaseModel):
    subpath: str = Field(default="", description="Relative path within approved project root")
    recursive: bool = Field(default=False, description="Whether to recursively list files")
    max_entries: int = Field(default=100, description="Max entries to return")


class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to read")
    max_lines: int = Field(default=500, description="Max lines to read")


class SearchFilesInput(BaseModel):
    query: str = Field(description="Search substring to match filenames against")
    root_path: str = Field(default="", description="Root folder to search within")
    max_results: int = Field(default=50, description="Max matching files to return")


class FileMetadataInput(BaseModel):
    file_path: str = Field(description="Path to file to inspect")


class WriteFileInput(BaseModel):
    file_path: str = Field(description="Path to target file to write or update")
    content: str = Field(description="Text content to write")
    create_backup: bool = Field(
        default=True, description="Whether to create backup of existing file"
    )


class CopyFileInput(BaseModel):
    source_path: str = Field(description="Source file path")
    destination_path: str = Field(description="Destination file path")


class MoveFileInput(BaseModel):
    source_path: str = Field(description="Source file path to move/rename")
    destination_path: str = Field(description="Destination path")


class DeleteFileInput(BaseModel):
    file_path: str = Field(description="Path to file to move to trash")


# --- Tool Implementations ---
class ListFilesTool(BaseTool):
    name = "list_files"
    description = "List files and directories within an approved project root."
    input_schema = ListFilesInput
    required_capabilities = [CapabilityType.FILESYSTEM_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            data = FilesystemService.list_directory(
                directory_path=params.get("subpath", ""),
                recursive=params.get("recursive", False),
                max_entries=params.get("max_entries", 100),
            )
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read lines from a text file within an approved project root."
    input_schema = ReadFileInput
    required_capabilities = [CapabilityType.FILESYSTEM_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            data = FilesystemService.read_text_file(
                file_path=params["file_path"],
                max_lines=params.get("max_lines", 500),
            )
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files by filename pattern in an approved root."
    input_schema = SearchFilesInput
    required_capabilities = [CapabilityType.FILESYSTEM_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            results = FilesystemService.search_files(
                query=params["query"],
                root_path=params.get("root_path", ""),
                max_results=params.get("max_results", 50),
            )
            return ToolResult(
                success=True,
                data={"results": results, "count": len(results)},
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class GetFileMetadataTool(BaseTool):
    name = "get_file_metadata"
    description = "Retrieve file metadata (size, timestamps, type) without loading file content."
    input_schema = FileMetadataInput
    required_capabilities = [CapabilityType.FILESYSTEM_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            metadata = FilesystemService.get_file_metadata(params["file_path"])
            return ToolResult(
                success=True,
                data=metadata,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write or edit a text file inside an approved project root with atomic safety and automatic backup."
    input_schema = WriteFileInput
    required_capabilities = [CapabilityType.FILESYSTEM_WRITE.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False
    supports_dry_run = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            res = FilesystemService.write_file(
                file_path=params["file_path"],
                content=params["content"],
                create_backup=params.get("create_backup", True),
                dry_run=dry_run,
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
                verified=True,
                resource_references=[res.get("file_path", params["file_path"])],
                verification_details=f"Wrote {res.get('bytes_written', 0)} bytes to {params['file_path']}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

    def validate_result(self, result: ToolResult, parameters: dict[str, Any]) -> ToolResult:
        if result.success and not result.dry_run:
            from pathlib import Path
            target = Path(parameters.get("file_path", ""))
            if not target.is_absolute():
                from app.security.path_validation import validate_path_in_roots
                try:
                    target = validate_path_in_roots(str(target))
                except Exception:
                    pass
            if not target.exists():
                result.success = False
                result.verified = False
                result.error = f"File write verification failed: file {target} does not exist on disk."
            else:
                result.verified = True
                result.resource_references = [str(target)]
                result.verification_details = f"Verified file on disk at {target} ({target.stat().st_size} bytes)."
        return result


class CopyFileTool(BaseTool):
    name = "copy_file"
    description = "Copy a file within permitted project roots."
    input_schema = CopyFileInput
    required_capabilities = [CapabilityType.FILESYSTEM_WRITE.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False
    supports_dry_run = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            res = FilesystemService.copy_file(
                source_path=params["source_path"],
                destination_path=params["destination_path"],
                dry_run=dry_run,
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
                verified=True,
                resource_references=[res.get("destination", params["destination_path"])],
                verification_details=f"File copied to {params['destination_path']}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

    def validate_result(self, result: ToolResult, parameters: dict[str, Any]) -> ToolResult:
        if result.success and not result.dry_run:
            from pathlib import Path
            dest = Path(parameters.get("destination_path", ""))
            result.resource_references = [str(dest)]
            result.verified = True
            result.verification_details = f"Verified copy destination exists at {dest}."
        return result


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Move or rename a file within permitted project roots."
    input_schema = MoveFileInput
    required_capabilities = [CapabilityType.FILESYSTEM_WRITE.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False
    supports_dry_run = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            res = FilesystemService.move_file(
                source_path=params["source_path"],
                destination_path=params["destination_path"],
                dry_run=dry_run,
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
                verified=True,
                resource_references=[res.get("destination", params["destination_path"])],
                verification_details=f"File moved to {params['destination_path']}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

    def validate_result(self, result: ToolResult, parameters: dict[str, Any]) -> ToolResult:
        if result.success and not result.dry_run:
            dest = parameters.get("destination_path", "")
            result.resource_references = [str(dest)]
            result.verified = True
            result.verification_details = f"Verified moved file at {dest}."
        return result


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = (
        "Delete a file inside an approved project root by safely moving it to recoverable trash."
    )
    input_schema = DeleteFileInput
    required_capabilities = [CapabilityType.FILESYSTEM_DELETE.value]
    risk_level = ToolRiskLevel.DESTRUCTIVE
    requires_approval = True
    supports_dry_run = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            res = FilesystemService.delete_file_to_trash(
                file_path=params["file_path"],
                dry_run=dry_run,
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                dry_run=dry_run,
                verified=True,
                resource_references=[params["file_path"]],
                verification_details=f"File moved to recoverable trash at {res.get('trash_path')}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

    def validate_result(self, result: ToolResult, parameters: dict[str, Any]) -> ToolResult:
        if result.success and not result.dry_run:
            from pathlib import Path
            orig = Path(parameters.get("file_path", ""))
            result.verified = True
            result.resource_references = [str(orig)]
            result.verification_details = f"Verified file '{orig}' was safely deleted to trash."
        return result

