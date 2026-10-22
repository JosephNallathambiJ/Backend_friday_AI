"""Dedicated Omni OSINT Power Adapter.

Provides capability discovery, health checks, credential validation,
typed requests/responses, rate limiting, source attribution, credential redaction,
and mock mode for development and testing.
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.omni_osint.models import (
    OmniCapabilities,
    OSINTConnectionStatus,
    OSINTQueryRequest,
    OSINTQueryResponse,
    OSINTRecord,
    OSINTSourceType,
    SourceAttribution,
)

logger = logging.getLogger("friday.omni_osint")

# Patterns for credential/token redaction
SENSITIVE_PATTERNS = [
    (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{10,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(api[_\-]?key\s*[:=]\s*)['\"]?[a-zA-Z0-9_\-]{8,}['\"]?", re.IGNORECASE), r"\1[REDACTED_KEY]"),
    (re.compile(r"(password\s*[:=]\s*)['\"][^'\"]+['\"]", re.IGNORECASE), r"\1[REDACTED_PASSWORD]"),
    (re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", re.IGNORECASE), r"[REDACTED_EMAIL]"),
]


def redact_sensitive_data(text: str) -> str:
    """Mask credentials, tokens, and private emails in intelligence outputs."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class OmniOSINTAdapter:
    """Robust integration adapter for Omni OSINT Power."""

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        mock_mode: bool | None = None,
        timeout: float | None = None,
        rate_limit_per_minute: int = 60,
    ):
        self.endpoint = (endpoint or settings.OMNI_OSINT_ENDPOINT).rstrip("/")
        self.api_key = api_key or settings.OMNI_OSINT_API_KEY
        self.mock_mode = settings.OMNI_OSINT_MOCK_MODE if mock_mode is None else mock_mode
        self.timeout = timeout or settings.OMNI_OSINT_TIMEOUT
        self.rate_limit_per_minute = rate_limit_per_minute

        self._query_timestamps: list[float] = []
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        """Truthful indicator of whether live Omni OSINT credentials and endpoints are configured."""
        return bool(self.api_key and settings.OMNI_OSINT_ENABLED and not self.mock_mode)

    def get_capabilities(self) -> OmniCapabilities:
        """Discover capabilities and current status."""
        status = self._evaluate_status()
        return OmniCapabilities(
            supported_queries=["domain", "ip", "subdomain_enum", "cert_transparency", "whois", "threat_intel"],
            rate_limit_per_minute=self.rate_limit_per_minute,
            supports_bulk=False,
            mock_mode=self.mock_mode,
            connection_status=status,
            required_env_vars=["OMNI_OSINT_ENDPOINT", "OMNI_OSINT_API_KEY"],
        )

    def _evaluate_status(self) -> OSINTConnectionStatus:
        if self.mock_mode:
            return OSINTConnectionStatus.MOCK_MODE
        if not self.api_key or not settings.OMNI_OSINT_ENABLED:
            return OSINTConnectionStatus.NOT_CONNECTED
        return OSINTConnectionStatus.CONNECTED

    async def check_health(self) -> dict[str, Any]:
        """Perform health and connectivity check."""
        status = self._evaluate_status()
        if self.mock_mode:
            return {
                "status": status.value,
                "connected": False,
                "mock_mode": True,
                "endpoint": self.endpoint,
                "message": (
                    "Omni OSINT Power is operating in MOCK MODE for safe offline development and testing. "
                    "Set OMNI_OSINT_MOCK_MODE=False and provide OMNI_OSINT_API_KEY to connect to a live service."
                ),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        if status == OSINTConnectionStatus.NOT_CONNECTED:
            return {
                "status": status.value,
                "connected": False,
                "mock_mode": False,
                "endpoint": self.endpoint,
                "message": (
                    "Omni OSINT Power integration is NOT CONNECTED. "
                    "External service endpoint or API key is unconfigured. "
                    "To enable live connectivity, configure OMNI_OSINT_ENDPOINT and OMNI_OSINT_API_KEY in environment."
                ),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        # Attempt live ping
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5.0)) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                resp = await client.get(f"{self.endpoint}/health", headers=headers)
                if resp.status_code == 200:
                    return {
                        "status": OSINTConnectionStatus.CONNECTED.value,
                        "connected": True,
                        "mock_mode": False,
                        "endpoint": self.endpoint,
                        "message": "Omni OSINT Power service is reachable and responsive.",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                return {
                    "status": OSINTConnectionStatus.DEGRADED.value,
                    "connected": False,
                    "mock_mode": False,
                    "endpoint": self.endpoint,
                    "status_code": resp.status_code,
                    "message": f"Omni OSINT Power service returned HTTP {resp.status_code}.",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
        except Exception as e:
            logger.warning("Omni OSINT live health check failed: %s", str(e))
            return {
                "status": OSINTConnectionStatus.NOT_CONNECTED.value,
                "connected": False,
                "mock_mode": False,
                "endpoint": self.endpoint,
                "error": str(e),
                "message": f"Failed to connect to Omni OSINT Power service at {self.endpoint}.",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def _enforce_rate_limit(self) -> None:
        """Sliding-window rate limit check."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            cutoff = now - 60.0
            self._query_timestamps = [t for t in self._query_timestamps if t > cutoff]
            if len(self._query_timestamps) >= self.rate_limit_per_minute:
                raise RuntimeError(
                    f"Omni OSINT rate limit exceeded: maximum {self.rate_limit_per_minute} queries per minute."
                )
            self._query_timestamps.append(now)

    def _validate_input(self, target: str) -> None:
        """Validate input targets and reject illegal private data transfers."""
        clean = target.strip().lower()
        if not clean:
            raise ValueError("Target cannot be empty.")
        # Reject file paths or private indicators
        if clean.startswith("/") or clean.startswith("c:\\") or clean.startswith("~"):
            raise ValueError(
                f"Invalid target '{target}': Local file paths must never be transmitted to external OSINT services."
            )
        if any(w in clean for w in ["password", "token", "secret", "bearer", "private_key"]):
            raise ValueError(
                "Security policy violation: Potential secrets or tokens detected in query target."
            )

    async def query(self, request: OSINTQueryRequest) -> OSINTQueryResponse:
        """Execute OSINT intelligence query with validation, rate limits, and provenance."""
        self._validate_input(request.target)
        await self._enforce_rate_limit()

        target = request.target.strip()
        status = self._evaluate_status()

        if self.mock_mode or status != OSINTConnectionStatus.CONNECTED:
            return self._generate_mock_response(target, request)

        # Live query execution
        return await self._execute_live_query(target, request)

    async def _execute_live_query(self, target: str, request: OSINTQueryRequest) -> OSINTQueryResponse:
        """Query live Omni OSINT Power API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "target": target,
                    "target_type": request.target_type,
                    "subdomains": request.include_subdomains,
                    "whois": request.include_whois,
                    "certificates": request.include_certificates,
                    "threat_intel": request.include_threat_intel,
                }
                resp = await client.post(f"{self.endpoint}/v1/query", json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error("Omni OSINT live API returned HTTP %s", resp.status_code)
                    return OSINTQueryResponse(
                        target=target,
                        status=OSINTConnectionStatus.DEGRADED,
                        is_mock=False,
                        summary=f"Omni OSINT service returned HTTP error: {resp.status_code}",
                        warnings=[f"Live query failed with HTTP {resp.status_code}"],
                    )

                data = resp.json()
                records: list[OSINTRecord] = []
                for item in data.get("records", []):
                    attr = SourceAttribution(
                        source_name="Omni OSINT Power (Live)",
                        source_type=OSINTSourceType(item.get("type", "infrastructure")),
                        confidence_score=float(item.get("confidence", 0.9)),
                        data_provider="Omni OSINT Global Feed",
                    )
                    records.append(
                        OSINTRecord(
                            indicator=redact_sensitive_data(item.get("indicator", target)),
                            indicator_type=item.get("indicator_type", "domain"),
                            category=item.get("category", "infrastructure"),
                            details=item.get("details", {}),
                            attribution=attr,
                            raw_snippet=redact_sensitive_data(item.get("raw_snippet", "")),
                        )
                    )

                return OSINTQueryResponse(
                    target=target,
                    status=OSINTConnectionStatus.CONNECTED,
                    is_mock=False,
                    records=records,
                    summary=f"Retrieved {len(records)} intelligence records from Omni OSINT Power live feed.",
                    metadata={"live_endpoint": self.endpoint, "records_count": len(records)},
                )
        except httpx.TimeoutException:
            logger.warning("Omni OSINT live query timed out for target: %s", target)
            return OSINTQueryResponse(
                target=target,
                status=OSINTConnectionStatus.DEGRADED,
                is_mock=False,
                summary=f"Omni OSINT live query timed out after {self.timeout}s.",
                warnings=[f"Request timed out after {self.timeout}s"],
            )
        except Exception as e:
            logger.exception("Omni OSINT live query exception")
            return OSINTQueryResponse(
                target=target,
                status=OSINTConnectionStatus.DEGRADED,
                is_mock=False,
                summary=f"Omni OSINT query failed: {str(e)}",
                warnings=[str(e)],
            )

    def _generate_mock_response(self, target: str, request: OSINTQueryRequest) -> OSINTQueryResponse:
        """Generate high-fidelity, deterministic mock OSINT findings for offline testing."""
        records: list[OSINTRecord] = []

        # 1. Passive DNS records
        dns_attr = SourceAttribution(
            source_name="Omni OSINT Power (Mock)",
            source_type=OSINTSourceType.PASSIVE_DNS,
            confidence_score=0.95,
            data_provider="Mock Passive DNS Registry",
        )
        records.append(
            OSINTRecord(
                indicator=target,
                indicator_type="domain",
                category="DNS",
                details={
                    "a_records": ["93.184.216.34"],
                    "mx_records": [f"mail.{target}", f"alt1.mail.{target}"],
                    "ns_records": [f"ns1.{target}", f"ns2.{target}"],
                    "txt_records": ["v=spf1 include:_spf.google.com ~all"],
                },
                attribution=dns_attr,
            )
        )

        # 2. Certificate transparency
        if request.include_certificates:
            cert_attr = SourceAttribution(
                source_name="Omni OSINT Power (Mock)",
                source_type=OSINTSourceType.CERTIFICATE_TRANSPARENCY,
                confidence_score=0.98,
                data_provider="Mock Certificate Transparency Log",
            )
            records.append(
                OSINTRecord(
                    indicator=target,
                    indicator_type="certificate",
                    category="TLS/Certificates",
                    details={
                        "issuer": "Let's Encrypt Authority X3",
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_to": "2026-12-31T23:59:59Z",
                        "subject_alt_names": [target, f"www.{target}", f"api.{target}"],
                    },
                    attribution=cert_attr,
                )
            )

        # 3. Discovered subdomains
        if request.include_subdomains:
            sub_attr = SourceAttribution(
                source_name="Omni OSINT Power (Mock)",
                source_type=OSINTSourceType.SUBDOMAINS,
                confidence_score=0.88,
                data_provider="Mock Subdomain Enumerator",
            )
            for sub in ["api", "vpn", "mail", "portal", "dev"]:
                records.append(
                    OSINTRecord(
                        indicator=f"{sub}.{target}",
                        indicator_type="subdomain",
                        category="Enumeration",
                        details={"ip_hint": f"198.51.100.{len(sub)}", "active": True},
                        attribution=sub_attr,
                    )
                )

        # 4. Public WHOIS summary
        if request.include_whois:
            whois_attr = SourceAttribution(
                source_name="Omni OSINT Power (Mock)",
                source_type=OSINTSourceType.WHOIS,
                confidence_score=0.92,
                data_provider="Mock Public WHOIS Aggregator",
            )
            records.append(
                OSINTRecord(
                    indicator=target,
                    indicator_type="whois",
                    category="Registration",
                    details={
                        "registrar": "Example Registrar LLC",
                        "created_date": "2015-05-12T00:00:00Z",
                        "updated_date": "2025-05-10T11:20:00Z",
                        "status": "clientTransferProhibited",
                    },
                    attribution=whois_attr,
                    raw_snippet=f"Domain: {target}\nRegistrar: Example Registrar LLC\nStatus: Active",
                )
            )

        status_flag = OSINTConnectionStatus.MOCK_MODE if self.mock_mode else OSINTConnectionStatus.NOT_CONNECTED
        summary_note = (
            f"Retrieved {len(records)} mock intelligence records for target '{target}'."
            if self.mock_mode
            else f"Omni OSINT service NOT CONNECTED. Fallback mock generated {len(records)} test records."
        )

        return OSINTQueryResponse(
            target=target,
            status=status_flag,
            is_mock=True,
            records=records,
            summary=summary_note,
            metadata={"mock_generator": "OmniOSINTAdapter.MockEngine", "target": target},
            warnings=["Operating in offline mock mode: live intelligence requires external provider credentials."],
        )


# Global adapter instance
omni_osint_adapter = OmniOSINTAdapter()
