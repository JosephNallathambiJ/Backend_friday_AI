"""Unit tests for Tool Registry, PolicyEngine, CapabilityManager, and Planner."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planner import Planner
from app.domain.enums import CapabilityType, PolicyOutcome, ToolRiskLevel
from app.security.permissions import CapabilityManager
from app.security.policy import PolicyEngine
from app.security.privileged import (
    PrivilegedOperationError,
    PrivilegedOperationRequest,
    PrivilegedToolGateway,
)
from app.tools.registry import tool_registry


@pytest.mark.asyncio
async def test_capability_manager_grant_and_revoke(db_session: AsyncSession):
    # Test checking default capability
    is_read_granted = await CapabilityManager.is_capability_granted(
        db_session, capability=CapabilityType.FILESYSTEM_READ.value
    )
    assert is_read_granted is True

    # Test explicit revocation
    await CapabilityManager.revoke_capability(
        db_session, capability=CapabilityType.FILESYSTEM_READ.value
    )
    is_revoked = await CapabilityManager.is_capability_granted(
        db_session, capability=CapabilityType.FILESYSTEM_READ.value
    )
    assert is_revoked is False

    # Test re-granting
    await CapabilityManager.grant_capability(
        db_session, capability=CapabilityType.FILESYSTEM_READ.value
    )
    is_regranted = await CapabilityManager.is_capability_granted(
        db_session, capability=CapabilityType.FILESYSTEM_READ.value
    )
    assert is_regranted is True


@pytest.mark.asyncio
async def test_policy_engine_evaluation(db_session: AsyncSession):
    # Safe read-only action
    res_allow = await PolicyEngine.evaluate_action(
        db=db_session,
        tool_name="list_files",
        risk_level=ToolRiskLevel.READ_ONLY,
        required_capabilities=[CapabilityType.FILESYSTEM_READ.value],
        parameters={},
    )
    assert res_allow.outcome == PolicyOutcome.ALLOW

    # Action requiring missing capability
    res_deny = await PolicyEngine.evaluate_action(
        db=db_session,
        tool_name="custom_tool",
        risk_level=ToolRiskLevel.READ_ONLY,
        required_capabilities=["nonexistent.capability"],
        parameters={},
    )
    assert res_deny.outcome == PolicyOutcome.DENY
    assert "missing required capabilities" in res_deny.reason

    # Destructive action requiring approval (grant capability first)
    await CapabilityManager.grant_capability(
        db_session, capability=CapabilityType.FILESYSTEM_DELETE.value
    )
    res_approval = await PolicyEngine.evaluate_action(
        db=db_session,
        tool_name="delete_file",
        risk_level=ToolRiskLevel.DESTRUCTIVE,
        required_capabilities=[CapabilityType.FILESYSTEM_DELETE.value],
        parameters={"file_path": "test.txt"},
        requires_approval=True,
    )
    assert res_approval.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert res_approval.requires_approval is True


@pytest.mark.asyncio
async def test_privileged_tool_gateway():
    # Permitted privileged operation
    req_status = PrivilegedOperationRequest(
        operation_name="system.time_sync_status",
        target_resource="clock",
    )
    result = await PrivilegedToolGateway.execute_privileged_operation(req_status)
    assert result["success"] is True

    # Prohibited privileged operation
    req_bad = PrivilegedOperationRequest(
        operation_name="system.spawn_root_shell",
        target_resource="terminal",
    )
    with pytest.raises(PrivilegedOperationError):
        await PrivilegedToolGateway.execute_privileged_operation(req_bad)


def test_planner_plan_generation():
    # Web research plan
    web_plan = Planner.generate_plan("search for latest Python 3.12 release notes")
    assert len(web_plan.steps) >= 1
    assert web_plan.steps[0].tool_name == "web_search"

    # Direct URL navigation plan
    url_plan = Planner.generate_plan("inspect https://example.com/docs")
    assert len(url_plan.steps) >= 1
    assert url_plan.steps[0].tool_name == "fetch_webpage"

    # File listing plan
    file_plan = Planner.generate_plan("list files in this repository")
    assert file_plan.steps[0].tool_name == "list_files"


def test_tool_registry_discovery():
    tools = tool_registry.list_tools()
    tool_names = [t.name for t in tools]

    expected = [
        "list_files",
        "read_file",
        "search_files",
        "write_file",
        "copy_file",
        "move_file",
        "delete_file",
        "web_search",
        "fetch_webpage",
        "browser_navigate",
        "get_system_info",
        "search_contacts",
    ]
    for exp in expected:
        assert exp in tool_names
