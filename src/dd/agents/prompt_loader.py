"""Runtime prompt loader with validation, versioning, and SHA-256 integrity checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

REQUIRED_SECTIONS = [
    "## Role",
    "## Inputs",
    "## Output schema",
    "## Rules",
    "## Stop / fail conditions",
    "## Tools allowed",
]

AGENT_FILE_MAP: dict[str, str] = {
    "planner": "planner.md",
    "extractor": "extractor.md",
    "linker": "linker.md",
    "red_team": "redteam.md",
    "redteam": "redteam.md",
    "verifier": "verifier.md",
    "reporter": "reporter.md",
    "remediation": "remediation.md",
    "risk": "risk.md",
}


@dataclass(frozen=True)
class PromptInfo:
    """Parsed prompt file metadata and content."""

    agent_name: str
    file_name: str
    version: str
    sha256: str
    content: str

    def __str__(self) -> str:
        return self.content


_PROMPT_CACHE: dict[str, PromptInfo] = {}


def clear_prompt_cache() -> None:
    """Clear in-memory prompt cache (used in testing or reload)."""
    _PROMPT_CACHE.clear()


def get_prompt(agent_name: str, prompts_dir: Path | None = None) -> PromptInfo:
    """Load, validate, hash, and return prompt for the specified agent.

    Fails loudly if the file is missing or lacks required sections.
    """
    normalized_name = agent_name.lower().strip()
    cache_key = normalized_name

    if cache_key in _PROMPT_CACHE and prompts_dir is None:
        return _PROMPT_CACHE[cache_key]

    base_dir = prompts_dir or PROMPTS_DIR
    file_name = AGENT_FILE_MAP.get(normalized_name, f"{normalized_name}.md")
    prompt_path = base_dir / file_name

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file for agent '{agent_name}' not found: {prompt_path}"
        )

    raw_content = prompt_path.read_text(encoding="utf-8")

    # 1. Parse version
    version_match = re.search(r"(?im)^version:\s*([^\s#]+)", raw_content)
    if not version_match:
        raise ValueError(
            f"Prompt file '{file_name}' lacks a valid 'version:' declaration."
        )
    version = version_match.group(1).strip()

    # 2. Validate required sections
    for section in REQUIRED_SECTIONS:
        if section not in raw_content:
            raise ValueError(
                f"Prompt file '{file_name}' is missing required section: '{section}'."
            )

    # 3. Compute SHA-256 of raw content
    sha256_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

    prompt_info = PromptInfo(
        agent_name=normalized_name,
        file_name=file_name,
        version=version,
        sha256=sha256_hash,
        content=raw_content,
    )

    if prompts_dir is None:
        _PROMPT_CACHE[cache_key] = prompt_info

    return prompt_info
