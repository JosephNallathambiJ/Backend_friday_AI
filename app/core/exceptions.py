"""Application exceptions and error definitions."""

from typing import Any


class FridayException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="NOT_FOUND", status_code=404, details=details)


class ValidationError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)


class SecurityPolicyError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="SECURITY_VIOLATION", status_code=403, details=details)


class ApprovalRequiredError(FridayException):
    def __init__(self, approval_id: str, message: str = "Approval required before execution"):
        super().__init__(
            message,
            code="APPROVAL_REQUIRED",
            status_code=403,
            details={"approval_id": approval_id},
        )


class ProviderError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="PROVIDER_ERROR", status_code=502, details=details)


class TaskCancelledError(FridayException):
    def __init__(self, message: str = "Task execution was cancelled"):
        super().__init__(message, code="TASK_CANCELLED", status_code=409)


class DependencyMissingError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="DEPENDENCY_MISSING", status_code=503, details=details)


class ModelNotInstalledError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="MODEL_NOT_INSTALLED", status_code=503, details=details)


class ModelUnavailableError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="MODEL_UNAVAILABLE", status_code=503, details=details)


class MalformedToolCallError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="MALFORMED_TOOL_CALL", status_code=422, details=details)


class TaskBudgetExhaustedError(FridayException):
    def __init__(self, message: str = "Task execution budget has been exhausted", details: dict[str, Any] | None = None):
        super().__init__(message, code="BUDGET_EXHAUSTED", status_code=429, details=details)


class ModelTimeoutError(FridayException):
    def __init__(self, message: str = "Model request timed out", details: dict[str, Any] | None = None):
        super().__init__(message, code="MODEL_TIMEOUT", status_code=504, details=details)


class ToolUnavailableError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="TOOL_UNAVAILABLE", status_code=404, details=details)


class ToolExecutionError(FridayException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="TOOL_EXECUTION_ERROR", status_code=500, details=details)
