"""Integration tests for Dual-Brain Architecture, Specialist Routing, and Mathematical API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.enums import BrainType
from app.main import app
from app.services.dual_brain_service import (
    FridayBrainOrchestrator,
    ModelRouter,
)


@pytest.mark.asyncio
async def test_model_router_deterministic_decisions():
    """Verify deterministic routing to Left, Right, Math Engine, and Dual Brain."""
    # 1. General assistant query -> Left Brain
    dec_gen = ModelRouter.route_request("What is the capital of France?")
    assert dec_gen.selected_brain == BrainType.LEFT
    assert dec_gen.task_category == "general"

    # 2. Pure cybersecurity vulnerability triage -> Right Brain
    dec_cyber = ModelRouter.route_request("Perform a vulnerability triage and threat model on CVE-2024-12345")
    assert dec_cyber.selected_brain == BrainType.RIGHT
    assert dec_cyber.task_category == "cybersecurity"

    # 3. Pure mathematical calculation -> Deterministic Math Engine
    dec_math = ModelRouter.route_request("calculate 15 * 8 + sqrt(144)")
    assert dec_math.selected_brain == BrainType.DETERMINISTIC
    assert dec_math.task_category == "mathematics"

    # 4. Math problem with explanation -> Math Engine + Left Brain
    dec_math_exp = ModelRouter.route_request("Solve for x: x**2 - 25 = 0 and explain step by step")
    assert dec_math_exp.selected_brain == BrainType.LEFT
    assert dec_math_exp.requires_math_engine is True

    # 5. Coding with security review -> Dual Brain Collaborative
    dec_dual = ModelRouter.route_request("Write code for user authentication and conduct a security review for SQL injection")
    assert dec_dual.selected_brain == BrainType.DUAL
    assert dec_dual.requires_secondary_review is True


@pytest.mark.asyncio
async def test_dual_brain_model_diagnostics():
    """Verify model diagnostics correctly inspect Ollama and detect installed models."""
    diag = await FridayBrainOrchestrator.get_model_diagnostics()
    assert "ollama_available" in diag
    assert "left_brain" in diag
    assert "right_brain" in diag
    # Left brain should be configured
    assert "LiquidAI" in diag["left_brain"]["configured"]
    # Right brain should be configured
    assert "Dolphin3" in diag["right_brain"]["configured"] or "Cyber" in diag["right_brain"]["configured"]


@pytest.mark.asyncio
async def test_dual_brain_collaborative_workflow_mocked(db_session):
    """Test full dual-brain collaboration flow (Left generates, Right reviews)."""
    result = await FridayBrainOrchestrator.execute_collaborative_workflow(
        session=db_session,
        user_prompt="Write a Python function to authenticate a user token and review it for timing attacks.",
        task_id="collab-test-1",
    )
    assert result["status"] == "completed"
    assert result["routing"] == "dual_brain_collaborative"
    assert "primary_solution" in result
    assert "security_review" in result
    assert "final_response" in result
    assert "Defensive Security Review" in result["final_response"]


@pytest.mark.asyncio
async def test_math_api_endpoints():
    """Verify all mathematical engine REST API endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Calculate endpoint
        calc_res = await ac.post("/api/v1/math/calculate", json={"expression": "100 / 4 + 7 * 3"})
        assert calc_res.status_code == 200
        data = calc_res.json()
        assert data["result"] == "46"
        assert data["computation_status"] == "exact"

        # 2. Solve algebraic equation
        solve_res = await ac.post("/api/v1/math/solve", json={"equation": "x**2 - 49", "variable": "x"})
        assert solve_res.status_code == 200
        solve_data = solve_res.json()
        assert "-7" in solve_data["result"] and "7" in solve_data["result"]

        # 3. Matrix algebra endpoint
        mat_res = await ac.post(
            "/api/v1/math/matrix",
            json={
                "operation": "determinant",
                "matrix_a": [[2.0, 0.0], [0.0, 5.0]],
            },
        )
        assert mat_res.status_code == 200
        assert mat_res.json()["result"] == 10.0

        # 4. Statistics endpoint
        stat_res = await ac.post(
            "/api/v1/math/statistics",
            json={"data": [10.0, 20.0, 30.0], "operation": "descriptive"},
        )
        assert stat_res.status_code == 200
        assert stat_res.json()["result"]["mean"] == 20.0

        # 5. Domains list
        dom_res = await ac.get("/api/v1/math/domains")
        assert dom_res.status_code == 200
        assert dom_res.json()["domains_count"] == 16


@pytest.mark.asyncio
async def test_dual_brain_api_endpoints(db_session):
    """Verify dual-brain routing and collaboration REST API endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Models diagnostic
        models_res = await ac.get("/api/v1/brain/models")
        assert models_res.status_code == 200
        assert "left_brain" in models_res.json()
        assert "right_brain" in models_res.json()

        # Decide route
        route_res = await ac.post(
            "/api/v1/brain/decide_route",
            json={"prompt": "Audit source code for buffer overflow vulnerabilities", "task_type": "security"},
        )
        assert route_res.status_code == 200
        assert route_res.json()["selected_brain"] == "right"

        # Execute pure math via brain route
        math_route_res = await ac.post(
            "/api/v1/brain/route",
            json={"prompt": "calculate 25 * 4", "task_type": "math"},
        )
        assert math_route_res.status_code == 200
        assert "100" in math_route_res.json()["final_response"]
