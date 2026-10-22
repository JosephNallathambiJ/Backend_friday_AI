"""Mandatory Target Authorization and Scope Enforcement for Cyber Agent.

Every active network recon, port scan, or system diagnosis job must record:
- Target or asset identifier.
- Target type.
- User-provided authorization or approved asset-scope reference.
- Allowed techniques and excluded targets.
- Rate and concurrency limits.
- Start time, operator, and job ID.
- Stop conditions and output-retention settings.
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import TargetType, TechniqueType


class TargetAuthorization(BaseModel):
    """Explicit authorization record for security scanning."""

    id: str = Field(default_factory=lambda: f"auth-{uuid4().hex[:12]}")
    target: str = Field(..., description="Target hostname, IP, CIDR, URL, or local asset")
    target_type: TargetType = Field(default=TargetType.DOMAIN)
    scope_reference: str = Field(..., description="Approval reference or asset scope identifier")
    allowed_techniques: list[TechniqueType] = Field(
        default_factory=lambda: [
            TechniqueType.PASSIVE_DNS,
            TechniqueType.PASSIVE_WHOIS,
            TechniqueType.CERTIFICATE_TRANSPARENCY,
            TechniqueType.HTTP_SECURITY_HEADERS,
            TechniqueType.DEPENDENCY_AUDIT,
            TechniqueType.SECRET_SCAN,
            TechniqueType.STATIC_CODE_ANALYSIS,
            TechniqueType.LOG_ANALYSIS,
        ]
    )
    excluded_targets: list[str] = Field(default_factory=list)
    rate_limit_rps: float = Field(default=2.0, ge=0.1, le=50.0)
    concurrency_limit: int = Field(default=2, ge=1, le=10)
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    operator: str = Field(default="system")
    job_id: str = Field(default_factory=lambda: f"job-{uuid4().hex[:8]}")
    stop_conditions: list[str] = Field(
        default_factory=lambda: ["high_error_rate", "operator_abort", "waf_block"]
    )
    output_retention: str = Field(default="ephemeral")
    active_recon_permitted: bool = Field(default=False)


class TargetAuthorizationManager:
    """Manages target authorizations, active scan permissions, and scoping rules."""

    def __init__(self):
        self._authorizations: dict[str, TargetAuthorization] = {}

    def register(self, auth: TargetAuthorization) -> TargetAuthorization:
        self._authorizations[auth.id] = auth
        return auth

    def create_authorization(
        self,
        target: str,
        scope_reference: str,
        target_type: TargetType = TargetType.DOMAIN,
        allowed_techniques: list[TechniqueType] | None = None,
        operator: str = "system",
        active_recon_permitted: bool = False,
    ) -> TargetAuthorization:
        auth = TargetAuthorization(
            target=target,
            scope_reference=scope_reference,
            target_type=target_type,
            allowed_techniques=allowed_techniques or [],
            operator=operator,
            active_recon_permitted=active_recon_permitted,
        )
        return self.register(auth)

    def get(self, auth_id: str) -> TargetAuthorization | None:
        return self._authorizations.get(auth_id)

    def list_all(self) -> list[TargetAuthorization]:
        return list(self._authorizations.values())

    @staticmethod
    def is_passive_technique(technique: TechniqueType) -> bool:
        """Passive techniques analyze public sources or static code without active network intrusion."""
        return technique in {
            TechniqueType.PASSIVE_DNS,
            TechniqueType.PASSIVE_WHOIS,
            TechniqueType.CERTIFICATE_TRANSPARENCY,
            TechniqueType.HTTP_SECURITY_HEADERS,
            TechniqueType.DEPENDENCY_AUDIT,
            TechniqueType.SECRET_SCAN,
            TechniqueType.STATIC_CODE_ANALYSIS,
            TechniqueType.LOG_ANALYSIS,
        }

    def validate_action(
        self,
        target: str,
        technique: TechniqueType,
        authorization_id: str | None = None,
    ) -> tuple[bool, str, TargetAuthorization | None]:
        """Validate whether an action is authorized against the target."""
        is_passive = self.is_passive_technique(technique)

        # Passive intelligence on public targets does not require prior privileged authorization
        if is_passive and not authorization_id:
            return True, f"Passive technique '{technique.value}' permitted under default public-source policy.", None

        if not authorization_id:
            return False, (
                f"Active technique '{technique.value}' strictly requires an explicit TargetAuthorization record. "
                f"No authorization_id provided for target: {target}."
            ), None

        auth = self._authorizations.get(authorization_id)
        if not auth:
            return False, f"TargetAuthorization record '{authorization_id}' was not found.", None

        # Check target match
        if target.lower() != auth.target.lower() and auth.target != "*":
            # Also check if target is in excluded list
            return False, f"Target '{target}' does not match authorized target '{auth.target}'.", auth

        if target.lower() in [ex.lower() for ex in auth.excluded_targets]:
            return False, f"Target '{target}' is explicitly listed in excluded targets.", auth

        # Check technique
        if technique not in auth.allowed_techniques:
            return False, f"Technique '{technique.value}' is not allowed in authorization scope.", auth

        # Check active permission
        if not is_passive and not auth.active_recon_permitted:
            return False, (
                f"Active network probing technique '{technique.value}' requires active_recon_permitted=True in authorization."
            ), auth

        # Check expiration
        if auth.expires_at and datetime.now(UTC) > auth.expires_at:
            return False, f"Authorization '{authorization_id}' expired at {auth.expires_at.isoformat()}.", auth

        return True, "Authorized", auth

    def is_authorized(self, target: str, authorization_id: str | None = None) -> bool:
        """Check if target has an active authorization or loopback self-test scope."""
        if target in {"localhost", "127.0.0.1", "::1"}:
            return True
        if authorization_id and authorization_id in self._authorizations:
            return True
        for auth in self._authorizations.values():
            if auth.target == target and auth.active_recon_permitted:
                return True
        return False


# Global target authorization manager
target_auth_manager = TargetAuthorizationManager()
