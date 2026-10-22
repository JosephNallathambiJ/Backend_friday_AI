"""Integration tests for Cyber APIs, Omni OSINT endpoints, and Diagnostics endpoints."""

import pytest
from starlette.testclient import TestClient

from app.main import app


def test_cyber_authorizations_api():
    """Test TargetAuthorization creation and retrieval via REST API."""
    client = TestClient(app)
    payload = {
        "target": "api.test-domain.org",
        "target_type": "domain",
        "scope_reference": "SEC-AUDIT-2026-QA",
        "allowed_techniques": ["passive_dns", "http_security_headers", "authorized_port_scan"],
        "rate_limit_rps": 3.0,
        "concurrency_limit": 2,
        "operator": "qa-tester",
        "active_recon_permitted": True,
    }

    create_res = client.post("/api/v1/cyber/authorizations", json=payload)
    assert create_res.status_code == 200
    created_data = create_res.json()["data"]
    auth_id = created_data["id"]
    assert auth_id.startswith("auth-")
    assert created_data["target"] == "api.test-domain.org"

    # List authorizations
    list_res = client.get("/api/v1/cyber/authorizations")
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] >= 1

    # Get single authorization
    get_res = client.get(f"/api/v1/cyber/authorizations/{auth_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == auth_id


def test_omni_osint_api_endpoints():
    """Test Omni OSINT capabilities, health, and query endpoints."""
    client = TestClient(app)
    # Capabilities
    caps_res = client.get("/api/v1/cyber/osint/capabilities")
    assert caps_res.status_code == 200
    caps_data = caps_res.json()["data"]
    assert "domain" in caps_data["supported_queries"]

    # Health
    health_res = client.get("/api/v1/cyber/osint/health")
    assert health_res.status_code == 200
    health_data = health_res.json()["data"]
    assert "mock_mode" in health_data

    # Query
    query_payload = {
        "target": "target-corp.com",
        "include_subdomains": True,
        "include_whois": True,
        "include_certificates": True,
    }
    query_res = client.post("/api/v1/cyber/osint/query", json=query_payload)
    assert query_res.status_code == 200
    res_data = query_res.json()["data"]
    assert res_data["target"] == "target-corp.com"
    assert len(res_data["records"]) >= 3


def test_diagnostics_api_endpoints():
    """Test running, querying, and listing backend diagnostics via REST API."""
    client = TestClient(app)
    # Run diagnostics
    run_res = client.post(
        "/api/diagnostics/run",
        json={
            "job_type": "diagnose",
            "run_static_checks": True,
            "run_runtime_checks": True,
            "run_model_checks": True,
        },
    )
    assert run_res.status_code == 200
    job_data = run_res.json()["data"]
    job_id = job_data["job_id"]
    assert job_id.startswith("diag-")
    assert job_data["total_checks"] >= 5

    # Retrieve diagnostics by ID
    get_res = client.get(f"/api/diagnostics/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["job_id"] == job_id

    # List diagnostics
    list_res = client.get("/api/diagnostics")
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_chatbot_coordinator_and_chat_alias(async_client):
    """Test conversational coordinator endpoint and /api/chat alias."""
    # Create conversation first
    conv_res = await async_client.post("/api/v1/conversations", json={"title": "Chat Coordinator API Test"})
    assert conv_res.status_code in {200, 201}
    conv_id = conv_res.json()["data"]["id"]

    # POST /api/v1/chat/coordinator
    coord_res = await async_client.post(
        "/api/v1/chat/coordinator",
        json={
            "conversation_id": conv_id,
            "message": "Calculate 50 * 4",
        },
    )
    assert coord_res.status_code == 200
    coord_data = coord_res.json()["data"]
    assert "200" in coord_data["content"]
    assert coord_data["routing"]["primary_agent"] == "math_engine"

    # POST /api/chat alias
    alias_res = await async_client.post(
        "/api/chat",
        json={
            "conversation_id": conv_id,
            "message": "Hello FRIDAY",
        },
    )
    assert alias_res.status_code == 200
    res_data = alias_res.json()["data"]
    assert "content" in res_data or "response" in res_data
