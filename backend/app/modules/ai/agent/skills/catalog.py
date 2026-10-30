"""Read-only SKILL.md catalog adapted from DeerFlow's parser and validation.

Only project-published resources are executable; no arbitrary filesystem or
development-assistant skill directories are exposed to the model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"^\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TOOL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_MAX_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    description: str
    allowed_tools: tuple[str, ...]
    content: str


def parse_skill(content: str) -> Skill:
    """Adapt DeerFlow's YAML frontmatter, validation and allowed-tools rules."""
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        raise ValueError("SKILL_FRONTMATTER_INVALID")
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError("SKILL_FRONTMATTER_INVALID") from exc
    if not isinstance(metadata, dict):
        raise ValueError("SKILL_FRONTMATTER_INVALID")
    # Secret binding and mutable/portable tool capabilities are intentionally
    # unsupported; never silently accept a declaration that implies them.
    if "required-secrets" in metadata or "secrets-autonomous" in metadata:
        raise ValueError("SKILL_SECRETS_UNSUPPORTED")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name) or len(name) > 64:
        raise ValueError("SKILL_NAME_INVALID")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024 or "<" in description or ">" in description:
        raise ValueError("SKILL_DESCRIPTION_INVALID")
    raw = metadata.get("allowed-tools", [])
    if isinstance(raw, str):
        raw = raw.split()
    if not isinstance(raw, list) or any(not isinstance(item, str) or not _TOOL_RE.fullmatch(item) for item in raw):
        raise ValueError("SKILL_TOOLS_INVALID")
    return Skill(name, description.strip(), tuple(dict.fromkeys(raw)), content[match.end() :].strip())


class SkillCatalog:
    """Load bounded, symlink-safe skill files from one server-owned directory."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(__file__).resolve().parent.parent / "resources" / "skills").resolve()

    def _load(self, name: str) -> Skill:
        if not _NAME_RE.fullmatch(name) or len(name) > 64:
            raise ValueError("SKILL_NAME_INVALID")
        path = (self.root / name / "SKILL.md").resolve()
        if not path.is_relative_to(self.root) or path.parent.name != name or not path.is_file():
            raise ValueError("SKILL_NOT_AVAILABLE")
        if path.stat().st_size > _MAX_BYTES:
            raise ValueError("SKILL_TOO_LARGE")
        skill = parse_skill(path.read_text(encoding="utf-8-sig"))
        if skill.name != name:
            raise ValueError("SKILL_NAME_MISMATCH")
        return skill

    def get(self, name: str, available_tools: set[str]) -> Skill:
        skill = self._load(name)
        if not set(skill.allowed_tools).issubset(available_tools):
            raise ValueError("SKILL_NOT_AVAILABLE")
        return skill

    def list(self, available_tools: set[str]) -> list[Skill]:
        if not self.root.is_dir():
            return []
        skills = []
        for path in sorted(self.root.iterdir()):
            if not path.is_dir():
                continue
            try:
                skills.append(self.get(path.name, available_tools))
            except (OSError, UnicodeError, ValueError):
                continue
        return skills

    def activate(self, names: list[str], available_tools: set[str]) -> list[Skill]:
        if len(names) > 16:
            raise ValueError("TOO_MANY_SKILLS")
        return [self.get(name, available_tools) for name in dict.fromkeys(names)]
