"""Unit tests for security policies: paths, commands, and secret redaction."""

from pathlib import Path

import pytest

from app.core.exceptions import SecurityPolicyError
from app.security.command_policy import validate_command
from app.security.path_validation import is_sensitive_path, validate_path_in_roots
from app.security.redaction import redact_dictionary


def test_path_validation_traversal_blocked(tmp_path):
    approved_dir = tmp_path / "project"
    approved_dir.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("classified")

    # Attempt path traversal
    with pytest.raises(SecurityPolicyError) as exc_info:
        validate_path_in_roots(
            target_path=str(approved_dir / ".." / "outside" / "secret.txt"),
            approved_roots=[str(approved_dir)],
        )
    assert "escapes approved project roots" in str(exc_info.value)


def test_sensitive_path_detection():
    assert is_sensitive_path(Path("/safe/path/.env")) is True
    assert is_sensitive_path(Path("/safe/path/id_rsa")) is True
    assert is_sensitive_path(Path("/safe/path/private.key")) is True
    assert is_sensitive_path(Path("/safe/path/.git/config")) is True
    assert is_sensitive_path(Path("/safe/path/main.py")) is False
    assert is_sensitive_path(Path("/safe/path/readme.md")) is False


def test_sensitive_file_access_blocked(tmp_path):
    approved_dir = tmp_path / "project"
    approved_dir.mkdir()
    env_file = approved_dir / ".env"
    env_file.write_text("SECRET=12345")

    with pytest.raises(SecurityPolicyError) as exc_info:
        validate_path_in_roots(target_path=str(env_file), approved_roots=[str(approved_dir)])
    assert "sensitive credential file" in str(exc_info.value)


def test_command_policy_prohibited_executables():
    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("sudo", ["apt-get", "update"])
    assert "strictly prohibited" in str(exc.value)

    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("rm", ["-rf", "/tmp"])
    assert "strictly prohibited" in str(exc.value)

    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("dd", ["if=/dev/zero"])
    assert "strictly prohibited" in str(exc.value)


def test_command_policy_unlisted_executable():
    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("unapproved_binary", [])
    assert "not in the list of allowed commands" in str(exc.value)


def test_command_policy_dangerous_patterns():
    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("git", ["status", "&&", "evil"])
    assert "chaining and subshell operators are prohibited" in str(exc.value)

    with pytest.raises(SecurityPolicyError) as exc:
        validate_command("git", ["status", ";", "evil"])
    assert "chaining and subshell operators are prohibited" in str(exc.value)


def test_command_policy_valid_command():
    # Should not raise
    validate_command("git", ["status", "--short"])
    validate_command("pytest", ["-v", "tests"])


def test_secret_redaction_strings_and_dicts():
    raw = {
        "api_key": "sk-live-1234567890abcdef",
        "nested": {
            "password": "supersecretpassword",
            "message": "Contact us with Bearer: secrettoken123",
            "normal_data": 42,
        },
        "safe_list": ["clean", "ghp_123456789012345678901234567890123456"],
    }
    redacted = redact_dictionary(raw)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert "supersecretpassword" not in str(redacted)
    assert redacted["nested"]["normal_data"] == 42
    assert "ghp_" not in str(redacted)
