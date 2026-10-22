"""Domain and API schemas using Pydantic v2."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.time import utc_now
from app.domain.enums import (
    ApprovalStatus,
    FindingSeverity,
    JobStatus,
    MemoryCategory,
    MessageRole,
    TaskStatus,
    ToolRiskLevel,
)


# Standard API envelope / responses
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class APIResponse(BaseModel):
    success: bool = True
    data: Any | None = None
    error: ErrorDetail | None = None


# Status & Health
class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=utc_now)


class SystemStatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    database_connected: bool
    ollama_connected: bool
    ollama_models: list[str]
    default_model: str
    cloud_enabled: bool
    scheduler_running: bool


# Conversation & Chat
class MessageCreate(BaseModel):
    role: MessageRole
    content: str
    tool_call_id: str | None = None
    name: str | None = None


class MessageRead(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata_json: dict[str, Any] | None = None


class ConversationCreate(BaseModel):
    title: str | None = "New Conversation"
    project_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None


class ConversationRead(BaseModel):
    id: str
    title: str
    project_id: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    model: str | None = None
    temperature: float | None = 0.7
    system_prompt: str | None = None
    enable_tools: bool = True


# Projects
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    root_path: str


class ProjectRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    root_path: str
    created_at: datetime
    updated_at: datetime
    approved_paths: list[str] = Field(default_factory=list)


# Memory
class MemoryCreate(BaseModel):
    category: MemoryCategory
    key: str
    content: str
    project_id: str | None = None
    metadata_json: dict[str, Any] | None = None


class MemoryRead(BaseModel):
    id: str
    category: MemoryCategory
    key: str
    content: str
    project_id: str | None = None
    created_at: datetime
    updated_at: datetime


# Approvals
class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalStatus  # APPROVED or REJECTED
    reason: str | None = None


class ApprovalRead(BaseModel):
    id: str
    task_id: str
    tool_name: str
    action_description: str
    risk_level: ToolRiskLevel
    arguments_redacted: dict[str, Any]
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime
    decision_reason: str | None = None


# Tasks
class TaskCreate(BaseModel):
    task_type: str
    summary: str
    project_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class TaskRead(BaseModel):
    id: str
    task_type: str
    summary: str
    project_id: str | None = None
    status: TaskStatus
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    result_data: dict[str, Any] | None = None


# Tools
class ToolRead(BaseModel):
    name: str
    description: str
    risk_level: ToolRiskLevel
    requires_approval: bool
    parameters_schema: dict[str, Any]


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    approval_id: str | None = None
    dry_run: bool = False


# Security
class SecurityScanRequest(BaseModel):
    target_path: str | None = None
    check_secrets: bool = True
    check_configs: bool = True
    check_dependencies: bool = True


class SecurityFindingRead(BaseModel):
    id: str
    title: str
    severity: FindingSeverity
    category: str
    file_path: str
    line_number: int | None = None
    evidence: str
    explanation: str
    remediation: str


class SecurityReportRead(BaseModel):
    id: str
    created_at: datetime
    summary: dict[str, int]
    findings: list[SecurityFindingRead]
    markdown_content: str


# Git
class GitStatusRead(BaseModel):
    branch: str
    is_clean: bool
    untracked_files: list[str]
    modified_files: list[str]
    staged_files: list[str]


class GitDiffRead(BaseModel):
    diff: str
    cached: bool


class GitCommitRead(BaseModel):
    sha: str
    author: str
    date: str
    message: str


# Schedules
class ScheduleCreate(BaseModel):
    name: str
    cron_expression: str | None = None
    interval_seconds: int | None = None
    task_type: str
    task_parameters: dict[str, Any] = Field(default_factory=dict)


class ScheduleRead(BaseModel):
    id: str
    name: str
    cron_expression: str | None = None
    interval_seconds: int | None = None
    task_type: str
    status: JobStatus
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
