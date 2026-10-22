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
    MANAGEMENT = "management"
    RESEARCH = "research"
    FILES = "files"
    CODING = "coding"
    TERMINAL = "terminal"
    PRIVILEGED = "privileged"
    SECURITY = "cybersecurity"
    ADMINISTRATION = "administration"
    COMPUTATION = "computation"
    TALKING = "talking"
    PATTERN = "pattern_recognition"
    LEARNING = "learning"
    SKILL_ACQUISITION = "skill_acquisition"
    BROWSER = "browser"
    DEVICE = "device"
    CONTACTS = "contacts"
    DEVELOPER = "developer"
    WORKFLOW = "workflow"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DATA_MEMORY = "data_memory"
    INTEGRATION = "integration"
    SCHEDULER = "scheduler"
    CHATBOT = "chatbot"
    DIAGNOSTICS = "backend_diagnostics"


class SkillExecutionMode(str, Enum):
    INSTRUCTION_ONLY = "instruction_only"
    WORKFLOW = "workflow"
    ADAPTER = "adapter"
    ISOLATED_PROCESS = "isolated_process"


class SkillStatus(str, Enum):
    INSTALLED = "installed"
    DISABLED = "disabled"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class AcquisitionStatus(str, Enum):
    QUEUED = "queued"
    SEARCHING = "searching"
    ACQUIRING = "acquiring"
    QUARANTINED = "quarantined"
    ANALYZING = "analyzing"
    TESTING = "testing"
    AWAITING_APPROVAL = "awaiting_approval"
    READY_TO_INSTALL = "ready_to_install"
    INSTALLED = "installed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


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


class BrainType(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    DUAL = "dual"
    DETERMINISTIC = "deterministic"


class DualBrainMode(str, Enum):
    SELECTIVE = "selective"
    COLLABORATIVE = "collaborative"
    SINGLE = "single"


class MathDomain(str, Enum):
    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    GEOMETRY = "geometry"
    CALCULUS = "calculus"
    LINEAR_ALGEBRA = "linear_algebra"
    DISCRETE_MATH = "discrete_math"
    PROBABILITY = "probability"
    STATISTICS = "statistics"
    NUMERICAL_METHODS = "numerical_methods"
    OPTIMIZATION = "optimization"
    INFORMATION_THEORY = "information_theory"
    FINANCIAL_MATH = "financial_math"
    PHYSICS_ENGINEERING = "physics_engineering"
    DATA_SCIENCE_ML = "data_science_ml"
    SIGNALS_TRANSFORMS = "signals_transforms"
    LOGIC_PROOFS = "logic_proofs"


class MathComputationStatus(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    ESTIMATED = "estimated"
    NUMERICALLY_UNSTABLE = "numerically_unstable"
    NOT_CONVERGED = "not_converged"
    UNSUPPORTED = "unsupported"
    INVALID_INPUT = "invalid_input"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class MathVerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    INDEPENDENTLY_CHECKED = "independently_checked"
    RESIDUAL_VALIDATED = "residual_validated"
    SUBSTITUTION_CONFIRMED = "substitution_confirmed"
    DISCREPANCY_DETECTED = "discrepancy_detected"


class TargetType(str, Enum):
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    CIDR = "cidr"
    URL = "url"
    REPOSITORY = "repository"
    LOCAL_HOST = "local_host"
    CONTAINER = "container"


class TechniqueType(str, Enum):
    PASSIVE_DNS = "passive_dns"
    PASSIVE_WHOIS = "passive_whois"
    CERTIFICATE_TRANSPARENCY = "certificate_transparency"
    HTTP_SECURITY_HEADERS = "http_security_headers"
    AUTHORIZED_PORT_SCAN = "authorized_port_scan"
    PORT_SCAN = "authorized_port_scan"
    DEPENDENCY_AUDIT = "dependency_audit"
    SECRET_SCAN = "secret_scan"
    STATIC_CODE_ANALYSIS = "static_code_analysis"
    LOG_ANALYSIS = "log_analysis"


class DiagnosticJobType(str, Enum):
    DIAGNOSE = "diagnose"
    DEBUG = "debug"
    TEST_WORKFLOW = "test_workflow"
    AUDIT_BACKEND = "audit_backend"
    VERIFY_FIX = "verify_fix"


class DiagnosticStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AudioFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    WEBM = "webm"
    M4A = "m4a"
