"""Filesystem security and path boundary validation."""

from pathlib import Path

from app.core.config import settings
from app.core.exceptions import SecurityPolicyError

# Default sensitive patterns that must never be read, indexed, or traversed
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    ".git/config",
    "credentials.json",
    "service_account.json",
    ".bash_history",
    ".zsh_history",
}

SENSITIVE_EXTENSIONS = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".pkcs12",
}


def is_sensitive_path(path: Path) -> bool:
    """Check if a path matches sensitive naming patterns."""
    name = path.name.lower()
    if name in SENSITIVE_NAMES:
        return True
    if any(path.name.endswith(ext) for ext in SENSITIVE_EXTENSIONS):
        return True
    # Check parts for sensitive directories
    for part in path.parts:
        if part in {".git", ".ssh", ".aws", ".gnupg"}:
            return True
    return False


def validate_path_in_roots(
    target_path: str | Path,
    approved_roots: list[str] | None = None,
    allow_sensitive: bool = False,
) -> Path:
    """Canonicalize and ensure a target path stays strictly inside approved project roots.

    Raises SecurityPolicyError if:
    - Target path traverses outside approved roots
    - Symbolic link resolves to an unapproved target
    - Path references sensitive configuration or credentials (unless explicitly allowed)
    """
    roots = approved_roots or settings.APPROVED_ROOTS
    if not roots:
        raise SecurityPolicyError("No approved project roots configured.")

    resolved_roots = [Path(r).resolve() for r in roots]

    # Resolve target path (handles .., symlinks)
    target = Path(target_path).resolve()

    # Check if target is inside at least one approved root
    is_inside = any(target == root or root in target.parents for root in resolved_roots)

    if not is_inside:
        raise SecurityPolicyError(
            f"Access denied: Path '{target}' escapes approved project roots: {[str(r) for r in resolved_roots]}"
        )

    # Check for sensitive credentials/keys
    if not allow_sensitive and is_sensitive_path(target):
        raise SecurityPolicyError(
            f"Access denied: '{target.name}' is classified as a sensitive credential file."
        )

    return target
