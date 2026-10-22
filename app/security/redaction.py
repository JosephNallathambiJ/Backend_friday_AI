"""Dictionary and data structure redaction utilities."""

from typing import Any

from app.core.logging import redact_sensitive_text

SENSITIVE_KEY_NAMES = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "private_key",
}


def redact_dictionary(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact dictionary keys and string values containing credentials."""
    if not isinstance(data, dict):
        return data

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = str(key).lower()
        if any(secret_term in key_lower for secret_term in SENSITIVE_KEY_NAMES):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_dictionary(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_dictionary(item)
                if isinstance(item, dict)
                else redact_sensitive_text(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            redacted[key] = redact_sensitive_text(value)
        else:
            redacted[key] = value

    return redacted
