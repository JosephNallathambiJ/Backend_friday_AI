"""Typed request and response models for Omni OSINT Power integration."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OSINTSourceType(str, Enum):
    PASSIVE_DNS = "passive_dns"
    WHOIS = "whois"
    CERTIFICATE_TRANSPARENCY = "certificate_transparency"
    THREAT_INTEL = "threat_intel"
    INFRASTRUCTURE = "infrastructure"
    SUBDOMAINS = "subdomains"


class OSINTConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    NOT_CONNECTED = "NOT CONNECTED"
    DEGRADED = "DEGRADED"
    MOCK_MODE = "MOCK MODE"


class SourceAttribution(BaseModel):
    """Provenance and source metadata for gathered intelligence."""

    source_name: str = "Omni OSINT Power"
    source_type: OSINTSourceType
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    data_provider: str = "Omni OSINT Intelligence Engine"
    reference_id: str = Field(default_factory=lambda: f"ref-{uuid4().hex[:8]}")


class OSINTRecord(BaseModel):
    """Normalized OSINT finding item."""

    indicator: str
    indicator_type: str
    category: str
    details: dict[str, Any] = Field(default_factory=dict)
    attribution: SourceAttribution
    raw_snippet: str | None = None


class OSINTQueryRequest(BaseModel):
    """Query payload sent to Omni OSINT Power adapter."""

    target: str = Field(..., description="Domain, IP, or CIDR to investigate")
    target_type: str = Field(default="domain")
    include_subdomains: bool = True
    include_whois: bool = True
    include_certificates: bool = True
    include_threat_intel: bool = True
    user_authorized_sharing: bool = Field(
        default=False,
        description="Explicit user consent to query external intelligence provider with this target.",
    )


class OSINTQueryResponse(BaseModel):
    """Normalized response from Omni OSINT Power adapter."""

    query_id: str = Field(default_factory=lambda: f"osint-{uuid4().hex[:8]}")
    target: str
    status: OSINTConnectionStatus
    is_mock: bool = False
    records: list[OSINTRecord] = Field(default_factory=list)
    summary: str
    queried_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OmniCapabilities(BaseModel):
    """Discovered capabilities of the Omni OSINT Power engine."""

    supported_queries: list[str] = Field(
        default_factory=lambda: ["domain", "ip", "subdomain_enum", "cert_transparency", "whois", "threat_intel"]
    )
    rate_limit_per_minute: int = 60
    supports_bulk: bool = False
    mock_mode: bool = True
    connection_status: OSINTConnectionStatus = OSINTConnectionStatus.NOT_CONNECTED
    required_env_vars: list[str] = Field(
        default_factory=lambda: ["OMNI_OSINT_ENDPOINT", "OMNI_OSINT_API_KEY"]
    )
