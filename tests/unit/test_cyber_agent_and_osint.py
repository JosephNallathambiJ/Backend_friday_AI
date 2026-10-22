"""Unit tests for CyberAgent, TargetAuthorization scoping, and Omni OSINT Power integration."""

import pytest

from app.agents.cyber_agent import CyberAgent
from app.domain.enums import TargetType, TechniqueType
from app.integrations.omni_osint import (
    OmniOSINTAdapter,
    OSINTConnectionStatus,
    OSINTQueryRequest,
    redact_sensitive_data,
)
from app.security.target_authorization import (
    TargetAuthorization,
    TargetAuthorizationManager,
)


@pytest.mark.asyncio
async def test_target_authorization_manager_passive_vs_active():
    """Verify that passive techniques are permitted by default but active scans require authorization."""
    mgr = TargetAuthorizationManager()

    # 1. Passive technique requires no prior authorization
    allowed, reason, auth = mgr.validate_action(
        target="example.com",
        technique=TechniqueType.PASSIVE_DNS,
        authorization_id=None,
    )
    assert allowed is True
    assert "Passive technique" in reason

    # 2. Active port probing strictly rejected without authorization
    allowed, reason, auth = mgr.validate_action(
        target="example.com",
        technique=TechniqueType.AUTHORIZED_PORT_SCAN,
        authorization_id=None,
    )
    assert allowed is False
    assert "strictly requires an explicit TargetAuthorization record" in reason


@pytest.mark.asyncio
async def test_target_authorization_scoping_rules():
    """Verify target matching, excluded targets, and active_recon_permitted enforcement."""
    mgr = TargetAuthorizationManager()

    # Create scoped authorization
    auth_rec = TargetAuthorization(
        target="192.168.1.50",
        target_type=TargetType.IP_ADDRESS,
        scope_reference="SEC-AUDIT-2026-ALPHA",
        allowed_techniques=[TechniqueType.AUTHORIZED_PORT_SCAN],
        excluded_targets=["192.168.1.1"],
        active_recon_permitted=True,
    )
    mgr.register(auth_rec)

    # 1. Matching target and authorized technique -> ALLOW
    allowed, reason, _ = mgr.validate_action(
        target="192.168.1.50",
        technique=TechniqueType.AUTHORIZED_PORT_SCAN,
        authorization_id=auth_rec.id,
    )
    assert allowed is True
    assert reason == "Authorized"

    # 2. Mismatched target -> DENY
    allowed, reason, _ = mgr.validate_action(
        target="192.168.1.99",
        technique=TechniqueType.AUTHORIZED_PORT_SCAN,
        authorization_id=auth_rec.id,
    )
    assert allowed is False
    assert "does not match authorized target" in reason

    # 3. Excluded target -> DENY
    auth_rec.excluded_targets.append("192.168.1.50")
    allowed, reason, _ = mgr.validate_action(
        target="192.168.1.50",
        technique=TechniqueType.AUTHORIZED_PORT_SCAN,
        authorization_id=auth_rec.id,
    )
    assert allowed is False
    assert "explicitly listed in excluded targets" in reason


@pytest.mark.asyncio
async def test_omni_osint_redaction_and_validation():
    """Verify that credentials, tokens, and private paths are redacted or rejected."""
    # Redaction test
    raw_text = "Connected using Bearer abcd1234efgh5678ijkl and api_key='sk_live_998877665544' email: admin@corp.org"
    cleaned = redact_sensitive_data(raw_text)
    assert "[REDACTED_TOKEN]" in cleaned
    assert "[REDACTED_KEY]" in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "sk_live_" not in cleaned

    # Input validation test
    adapter = OmniOSINTAdapter(mock_mode=True)
    with pytest.raises(ValueError, match="Local file paths must never be transmitted"):
        adapter._validate_input("/etc/shadow")

    with pytest.raises(ValueError, match="Potential secrets or tokens"):
        adapter._validate_input("password=my_secret_token")


@pytest.mark.asyncio
async def test_omni_osint_mock_mode_and_capabilities():
    """Verify Omni OSINT Power mock mode returns structured records and attribution."""
    adapter = OmniOSINTAdapter(mock_mode=True)
    caps = adapter.get_capabilities()
    assert caps.mock_mode is True
    assert "domain" in caps.supported_queries

    health = await adapter.check_health()
    assert health["mock_mode"] is True
    assert health["status"] == OSINTConnectionStatus.MOCK_MODE.value

    # Query mock intelligence
    req = OSINTQueryRequest(
        target="secure-company.com",
        include_subdomains=True,
        include_whois=True,
        include_certificates=True,
    )
    res = await adapter.query(req)
    assert res.is_mock is True
    assert res.target == "secure-company.com"
    assert len(res.records) >= 3

    # Check source attribution
    for record in res.records:
        assert record.attribution.source_name.startswith("Omni OSINT Power")
        assert record.attribution.confidence_score > 0.8


@pytest.mark.asyncio
async def test_cyber_agent_execution_flow(db_session):
    """Test CyberAgent execution with passive OSINT, secret detection, and report generation."""
    agent = CyberAgent()
    result = await agent.execute(
        task_id="task-cyber-unit-01",
        goal="Perform security audit on example.com",
        parameters={"target": "example.com", "action": "full_scan"},
        session=db_session,
    )

    assert result.success is True
    assert "Cyber analysis completed" in result.summary
    assert "markdown_report" in result.data
    assert len(result.tool_results) >= 3
