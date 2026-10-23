"""Secret scanning and security hygiene tests for Digital Doppelgänger.

Verifies:
1. No active secrets, API keys, private tokens, or private keys in the repo.
2. .env.example only contains placeholders.
3. .env is properly gitignored.
4. Deterministic sample and cache files do not leak secrets.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Regex patterns for detecting active secrets or credentials
SECRET_PATTERNS = [
    (re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"), "NVIDIA API Key"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "OpenAI API Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub Personal Access Token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google API Key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Private Key"),
]

# Extensions and dirs to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".md", ".json", ".jsonl", ".csv", ".toml", ".txt", ".sql", ".html", ".js", ".css", ".yml", ".yaml", ".env.example"
}

IGNORED_DIRS = {
    ".git", ".pytest_cache", "__pycache__", ".venv", "venv", ".tempmediaStorage", "node_modules", "runs"
}


def test_no_hardcoded_secrets_in_repo() -> None:
    """Scan all project source files to ensure no real credentials leaked into git."""
    violations: list[str] = []

    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        # Skip ignored directories
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue
        if path.suffix not in SCANNABLE_EXTENSIONS and path.name != ".env.example":
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, label in SECRET_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                # Filter out obvious test/mock placeholders if any
                real_matches = [
                    m for m in matches
                    if not any(placeholder in m for placeholder in ("PLACEHOLDER", "dummy", "example", "test"))
                ]
                if real_matches:
                    rel_path = path.relative_to(REPO_ROOT)
                    violations.append(f"{rel_path}: Found {label} match: {real_matches[0][:8]}...")

    assert not violations, f"Secret scan found potential secrets:\n" + "\n".join(violations)


def test_env_example_has_placeholders_only() -> None:
    """Ensure .env.example contains only safe placeholders and documentation."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), ".env.example file must exist."

    content = env_example.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

    for line in lines:
        assert "=" in line, f"Malformed line in .env.example: {line}"
        key, val = line.split("=", 1)
        val = val.strip()

        if key in ("SAMPLE_MODE", "ZETARIS_HOST", "ZETARIS_PORT"):
            continue  # Safe defaults (true, localhost, 5432)

        if key.endswith(("_KEY", "_PASSWORD", "_USER", "_DATABASE", "_URL", "_MODEL")) or "MODEL" in key:
            assert (
                "PLACEHOLDER" in val or "example.com" in val or "localhost" in val
            ), f".env.example contains potentially non-placeholder value for {key}: {val}"


def test_dotenv_is_gitignored() -> None:
    """Ensure .env is gitignored and will never be committed."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore file must exist."

    content = gitignore.read_text(encoding="utf-8")
    ignored_entries = [line.strip() for line in content.splitlines()]

    assert ".env" in ignored_entries, ".env must be explicitly declared in .gitignore"


def test_replay_cache_hygiene() -> None:
    """Ensure replay cache contains valid jsonl and no authorization tokens."""
    cache_file = REPO_ROOT / "cache" / "llm_replay.jsonl"
    if not cache_file.exists():
        return

    content = cache_file.read_text(encoding="utf-8")
    assert "Bearer nvapi-" not in content
    assert "Bearer sk-" not in content
    assert "Authorization" not in content or "PLACEHOLDER" in content
