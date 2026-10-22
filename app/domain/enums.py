"""Domain enumerations for FRIDAY AI."""

from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ToolRiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOCAL_MUTATION = "local_mutation"
    NETWORK_ACCESS = "network_access"
    DESTRUCTIVE = "destructive"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    FAILED = "failed"


class MemoryCategory(str, Enum):
    SESSION = "session"
    PROJECT = "project"
    PREFERENCE = "preference"
    TASK_SUMMARY = "task_summary"
    DOCUMENT_REF = "document_ref"


class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    FAILED = "failed"


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    FILES = "files"
    BROWSER = "browser"
    DEVICE = "device"
    CONTACTS = "contacts"
    DEVELOPER = "developer"
    WORKFLOW = "workflow"


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CapabilityType(str, Enum):
    SYSTEM_INFO_READ = "system.info.read"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_DELETE = "filesystem.delete"
    PROCESS_EXECUTE = "process.execute"
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_READ = "browser.read"
    BROWSER_INTERACT = "browser.interact"
    CONTACTS_READ = "contacts.read"
    CONTACTS_WRITE = "contacts.write"
    NOTIFICATIONS_SEND = "notifications.send"
    APPLICATIONS_LAUNCH = "applications.launch"
    NETWORK_FETCH = "network.fetch"
    SCHEDULED_TASKS_MANAGE = "scheduled_tasks.manage"


class ScopeType(str, Enum):
    GLOBAL = "global"
    DIRECTORY = "directory"
    DOMAIN = "domain"
    COMMAND = "command"
