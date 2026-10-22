"""Skill manifest schema, validation, and parsing for FRIDAY AI (friday-skill.yaml).

Defines the typed Pydantic contract for extensible agent skills acquired from GitHub
or locally managed. Rejects invalid identifiers, unsafe paths, and malformed definitions.
"""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.exceptions import ValidationError
from app.domain.enums import SkillExecutionMode, ToolRiskLevel

# Strict identifier regex: e.g. "github.com/org/repo" or "python-ast-analyzer"
SKILL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\./]+$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$")


class SkillManifest(BaseModel):
    """Authoritative typed schema for friday-skill.yaml manifests."""

    id: str = Field(description="Stable unique skill identifier, e.g. 'coding.ast-analyzer'")
    name: str = Field(description="Human-readable title of the skill")
    version: str = Field(default="1.0.0", description="SemVer version string")
    description: str = Field(description="Summary of capabilities provided by the skill")
    author: str = Field(default="Community", description="Author or organization name")
    license: str = Field(default="Unknown", description="SPDX license identifier (e.g. MIT, Apache-2.0)")
    source: str = Field(default="", description="Source repository URL (e.g. GitHub URL)")
    source_commit: str = Field(default="", description="Pinned commit SHA (40 hex characters)")
    entrypoint: str = Field(default="SKILL.md", description="Entrypoint path relative to skill root")
    supported_agents: list[str] = Field(default_factory=list, description="List of compatible agent IDs or names")
    supported_platforms: list[str] = Field(default_factory=lambda: ["all"], description="Supported OS platforms")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema of skill inputs")
    output_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema of skill outputs")
    required_capabilities: list[str] = Field(default_factory=list, description="FRIDAY capability permissions required")
    dependencies: list[str] = Field(default_factory=list, description="Required Python or package dependencies")
    network_requirements: list[str] = Field(default_factory=list, description="Outbound domains required (if any)")
    execution_mode: SkillExecutionMode = Field(
        default=SkillExecutionMode.INSTRUCTION_ONLY,
        description="Mode of execution (instruction_only, workflow, adapter, isolated_process)",
    )
    risk_level: ToolRiskLevel = Field(default=ToolRiskLevel.READ_ONLY, description="Assigned risk tier")
    tests: list[dict[str, Any]] = Field(default_factory=list, description="Test specifications and expected assertions")
    integrity_metadata: dict[str, Any] = Field(default_factory=dict, description="SHA256 checksums and provenance signatures")

    @field_validator("id")
    @classmethod
    def validate_skill_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean or len(clean) > 128:
            raise ValueError("Skill ID must be between 1 and 128 characters.")
        if not SKILL_ID_PATTERN.match(clean) or ".." in clean:
            raise ValueError(f"Invalid skill ID '{v}'. Must be alphanumeric with hyphens, underscores, dots, or slashes, and no directory traversal.")
        return clean

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        clean = v.strip()
        if not SEMVER_PATTERN.match(clean):
            # Tolerant fallback to digits if simple version
            if not re.match(r"^\d+(\.\d+)*$", clean):
                raise ValueError(f"Invalid semver version '{v}'. Expected format 'X.Y.Z'.")
        return clean

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, v: str) -> str:
        clean = v.strip()
        if ".." in clean or clean.startswith("/") or clean.startswith("\\"):
            raise ValueError("Entrypoint path cannot traverse directories or be absolute.")
        return clean


def parse_skill_manifest_from_yaml(content: str) -> SkillManifest:
    """Parse and validate YAML manifest string."""
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValidationError("Skill manifest must be a YAML dictionary.")
        return SkillManifest.model_validate(data)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Malformed YAML in skill manifest: {exc}") from exc
    except Exception as exc:
        raise ValidationError(f"Invalid skill manifest schema: {exc}") from exc


def load_manifest_from_directory(skill_dir: Path) -> SkillManifest:
    """Load friday-skill.yaml or SKILL.md frontmatter from a skill directory."""
    manifest_file = skill_dir / "friday-skill.yaml"
    if manifest_file.exists():
        return parse_skill_manifest_from_yaml(manifest_file.read_text(encoding="utf-8"))

    # Fallback: check friday-skill.yml or skill.json
    for alt in ["friday-skill.yml", "skill.json"]:
        alt_path = skill_dir / alt
        if alt_path.exists():
            return parse_skill_manifest_from_yaml(alt_path.read_text(encoding="utf-8"))

    # Synthesize from SKILL.md if present (e.g. Antigravity/Cursor style skills)
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        raw_text = skill_md.read_text(encoding="utf-8")
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                frontmatter_yaml = parts[1]
                data = yaml.safe_load(frontmatter_yaml) or {}
                # Populate defaults if missing
                if "id" not in data:
                    data["id"] = data.get("name", skill_dir.name).lower().replace(" ", "-")
                if "name" not in data:
                    data["name"] = data["id"].replace("-", " ").title()
                if "description" not in data:
                    data["description"] = f"Instruction skill for {data['name']}"
                return SkillManifest.model_validate(data)

    raise ValidationError(f"No valid friday-skill.yaml or SKILL.md found in {skill_dir}")
