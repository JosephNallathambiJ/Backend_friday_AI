"""Omni OSINT Power integration module."""

from app.integrations.omni_osint.adapter import (
    OmniOSINTAdapter,
    omni_osint_adapter,
    redact_sensitive_data,
)
from app.integrations.omni_osint.models import (
    OmniCapabilities,
    OSINTConnectionStatus,
    OSINTQueryRequest,
    OSINTQueryResponse,
    OSINTRecord,
    OSINTSourceType,
    SourceAttribution,
)

__all__ = [
    "OmniCapabilities",
    "OmniOSINTAdapter",
    "OSINTConnectionStatus",
    "OSINTQueryRequest",
    "OSINTQueryResponse",
    "OSINTRecord",
    "OSINTSourceType",
    "SourceAttribution",
    "omni_osint_adapter",
    "redact_sensitive_data",
]

# Aliases for case conventions
OmniOsintAdapter = OmniOSINTAdapter
OsintQueryRequest = OSINTQueryRequest
