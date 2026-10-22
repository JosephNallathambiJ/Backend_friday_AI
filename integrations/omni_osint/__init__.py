"""Forwarder package for integrations.omni_osint pointing to app.integrations.omni_osint."""

from app.integrations.omni_osint import (
    OmniCapabilities,
    OmniOSINTAdapter,
    OSINTConnectionStatus,
    OSINTQueryRequest,
    OSINTQueryResponse,
    OSINTRecord,
    OSINTSourceType,
    SourceAttribution,
    omni_osint_adapter,
    redact_sensitive_data,
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
