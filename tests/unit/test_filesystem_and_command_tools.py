"""Unit tests for FilesystemService, CommandRunnerService, and SSRF validation."""

from pathlib import Path

import pytest

from app.core.exceptions import SecurityPolicyError
from app.services.command_runner import CommandRunnerService
from app.services.filesystem_service import FilesystemService
from app.services.web_research_service import validate_public_url


def test_filesystem_atomic_write_and_backup():
    scratch_dir = Path.cwd() / "data" / "test_scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    test_file = scratch_dir / "sample.txt"
    try:
        # Write initial content
        res1 = FilesystemService.write_file(
            str(test_file), "Initial content v1", create_backup=True
        )
        assert res1["success"] is True
        assert test_file.read_text(encoding="utf-8") == "Initial content v1"

        # Overwrite with backup
        res2 = FilesystemService.write_file(
            str(test_file), "Updated content v2", create_backup=True
        )
        assert res2["success"] is True
        assert res2["backup_created"] is not None
        assert Path(res2["backup_created"]).exists()
        assert Path(res2["backup_created"]).read_text(encoding="utf-8") == "Initial content v1"
        assert test_file.read_text(encoding="utf-8") == "Updated content v2"
    finally:
        import shutil

        if scratch_dir.exists():
            shutil.rmtree(scratch_dir, ignore_errors=True)


def test_filesystem_recoverable_trash_deletion():
    scratch_dir = Path.cwd() / "data" / "test_scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    del_file = scratch_dir / "to_delete.txt"
    try:
        del_file.write_text("Sensitive data", encoding="utf-8")
        res = FilesystemService.delete_file_to_trash(str(del_file))
        assert res["success"] is True
        assert not del_file.exists()
        assert Path(res["trash_path"]).exists()
        assert Path(res["trash_path"]).read_text(encoding="utf-8") == "Sensitive data"
    finally:
        import shutil

        if scratch_dir.exists():
            shutil.rmtree(scratch_dir, ignore_errors=True)


def test_ssrf_validation_blocks_private_and_loopback():
    # Loopback strings
    with pytest.raises(SecurityPolicyError):
        validate_public_url("http://127.0.0.1:8080/admin")

    with pytest.raises(SecurityPolicyError):
        validate_public_url("http://localhost:5000/keys")

    with pytest.raises(SecurityPolicyError):
        validate_public_url("http://0.0.0.0/internal")

    # Cloud metadata link-local
    with pytest.raises(SecurityPolicyError):
        validate_public_url("http://169.254.169.254/latest/meta-data/")

    # Unsupported scheme
    with pytest.raises(SecurityPolicyError):
        validate_public_url("file:///etc/passwd")

    with pytest.raises(SecurityPolicyError):
        validate_public_url("ftp://ftp.example.com")


@pytest.mark.asyncio
async def test_command_runner_profiles_and_safety():
    # Valid command under system_check profile
    res = await CommandRunnerService.run_command(
        executable="uname",
        args=[],
        profile_name="system_check",
    )
    assert res.exit_code == 0
    assert len(res.stdout) > 0

    # Command chaining / shell metacharacter rejection
    with pytest.raises(SecurityPolicyError):
        await CommandRunnerService.run_command(
            executable="uname",
            args=["; rm -rf /"],
            profile_name="system_check",
        )

    # Prohibited executable
    with pytest.raises(SecurityPolicyError):
        await CommandRunnerService.run_command(
            executable="sudo",
            args=["whoami"],
            profile_name="system_check",
        )
