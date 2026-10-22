"""Integration tests for all REST API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_and_status(async_client: AsyncClient):
    # Liveness
    live_res = await async_client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # Readiness
    ready_res = await async_client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # Status
    status_res = await async_client.get("/api/v1/status")
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["app_name"] == "FRIDAY-AI-Backend"
    assert body["database_connected"] is True


@pytest.mark.asyncio
async def test_conversations_lifecycle(async_client: AsyncClient):
    # 1. Create
    res = await async_client.post("/api/v1/conversations", json={"title": "Test Thread"})
    assert res.status_code == 201
    data = res.json()["data"]
    conv_id = data["id"]
    assert data["title"] == "Test Thread"

    # 2. List
    list_res = await async_client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    assert any(c["id"] == conv_id for c in list_res.json()["data"])

    # 3. Add message
    msg_res = await async_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Hello FRIDAY!"},
    )
    assert msg_res.status_code == 201
    assert msg_res.json()["data"]["content"] == "Hello FRIDAY!"

    # 4. Get messages
    get_msgs_res = await async_client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert get_msgs_res.status_code == 200
    assert len(get_msgs_res.json()["data"]) >= 1

    # 5. Patch title
    patch_res = await async_client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "Updated Title"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["title"] == "Updated Title"

    # 6. Delete
    del_res = await async_client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 200

    # 7. Verify 404
    verify_res = await async_client.get(f"/api/v1/conversations/{conv_id}")
    assert verify_res.status_code == 404


@pytest.mark.asyncio
async def test_projects_and_retrieval(async_client: AsyncClient):
    proj_dir = Path.cwd() / "test_sample_proj"
    proj_dir.mkdir(exist_ok=True)
    doc_file = proj_dir / "guide.md"
    doc_file.write_text("FRIDAY AI architecture uses micro-modules and local-first SQLite.")

    try:
        # 1. Create project
        res = await async_client.post(
            "/api/v1/projects",
            json={"name": "SampleProj", "root_path": str(proj_dir)},
        )
        assert res.status_code == 201
        proj_id = res.json()["data"]["id"]

        # 2. Index project files
        index_res = await async_client.post(f"/api/v1/projects/{proj_id}/index")
        assert index_res.status_code == 200
        assert index_res.json()["data"]["files_indexed"] >= 1

        # 3. Search project
        search_res = await async_client.get(f"/api/v1/projects/{proj_id}/search?q=architecture")
        assert search_res.status_code == 200
        results = search_res.json()["data"]["results"]
        assert len(results) >= 1
        assert "guide.md" in results[0]["file_path"]
    finally:
        if doc_file.exists():
            doc_file.unlink()
        if proj_dir.exists():
            proj_dir.rmdir()


@pytest.mark.asyncio
async def test_memory_crud(async_client: AsyncClient):
    # Create memory
    res = await async_client.post(
        "/api/v1/memory",
        json={
            "category": "preference",
            "key": "theme",
            "content": "dark_mode_enabled",
        },
    )
    assert res.status_code == 201
    mem_id = res.json()["data"]["id"]

    # List
    list_res = await async_client.get("/api/v1/memory?category=preference")
    assert list_res.status_code == 200
    assert any(m["key"] == "theme" for m in list_res.json()["data"])

    # Delete
    del_res = await async_client.delete(f"/api/v1/memory/{mem_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_tasks_lifecycle(async_client: AsyncClient):
    # Create task
    res = await async_client.post(
        "/api/v1/tasks",
        json={"task_type": "security_audit", "summary": "Audit local directory"},
    )
    assert res.status_code == 201
    task_id = res.json()["data"]["id"]
    assert res.json()["data"]["status"] == "queued"

    # Cancel task
    cancel_res = await async_client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "cancelled"

    # Events
    events_res = await async_client.get(f"/api/v1/tasks/{task_id}/events")
    assert events_res.status_code == 200
    assert len(events_res.json()["data"]) >= 2


@pytest.mark.asyncio
async def test_tools_discovery_and_execution(async_client: AsyncClient):
    # Discovery
    res = await async_client.get("/api/v1/tools")
    assert res.status_code == 200
    tool_names = [t["name"] for t in res.json()["data"]]
    assert "list_files" in tool_names
    assert "run_terminal_command" in tool_names

    # Direct execution of read_only tool (list_files)
    exec_res = await async_client.post(
        "/api/v1/tools/execute",
        json={"tool_name": "list_files", "parameters": {"subpath": "."}},
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["data"]["success"] is True

    # Attempting to execute run_terminal_command without approval should be rejected
    fail_res = await async_client.post(
        "/api/v1/tools/execute",
        json={"tool_name": "run_terminal_command", "parameters": {"command": "git"}},
    )
    assert fail_res.status_code == 403


@pytest.mark.asyncio
async def test_git_status_and_diff(async_client: AsyncClient):
    status_res = await async_client.get("/api/v1/git/status")
    assert status_res.status_code == 200
    assert status_res.json()["success"] is True

    diff_res = await async_client.get("/api/v1/git/diff")
    assert diff_res.status_code == 200
    assert diff_res.json()["success"] is True


@pytest.mark.asyncio
async def test_security_scan_and_report(async_client: AsyncClient):
    res = await async_client.post("/api/v1/security/scan", json={"target_path": "."})
    assert res.status_code == 201
    report = res.json()["data"]
    assert "id" in report
    assert "summary" in report
    assert "markdown_content" in report

    # Fetch markdown
    report_id = report["id"]
    md_res = await async_client.get(f"/api/v1/reports/{report_id}/markdown")
    assert md_res.status_code == 200
    assert "Security Analysis Report" in md_res.text


@pytest.mark.asyncio
async def test_schedules_crud(async_client: AsyncClient):
    res = await async_client.post(
        "/api/v1/schedules",
        json={
            "name": "Daily-Security-Scan",
            "cron_expression": "0 0 * * *",
            "task_type": "security_scan",
        },
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["id"]

    # Pause
    pause_res = await async_client.post(f"/api/v1/schedules/{job_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "paused"

    # Resume
    resume_res = await async_client.post(f"/api/v1/schedules/{job_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["status"] == "active"

    # Delete
    del_res = await async_client.delete(f"/api/v1/schedules/{job_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_sanitized_settings(async_client: AsyncClient):
    res = await async_client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "api_key" not in data
    assert "cloud_api_key" not in data
    assert data["app_name"] == "FRIDAY-AI-Backend"
