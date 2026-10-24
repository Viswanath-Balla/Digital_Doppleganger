#!/usr/bin/env python3
"""Repeatable Hackathon Compliance and Judging-Readiness Audit Script.

Usage:
    python scripts/audit.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def report(name: str, status: str, details: str) -> bool:
    if status == "PASS":
        badge = f"{GREEN}[PASS]{RESET}"
    elif status == "PARTIAL":
        badge = f"{YELLOW}[PARTIAL]{RESET}"
    elif status == "FAIL":
        badge = f"{RED}[FAIL]{RESET}"
    else:
        badge = f"[HUMAN]"
    print(f"{badge} {BOLD}{name}{RESET}: {details}")
    return status == "PASS"


def check_required_files() -> bool:
    required = [
        "README.md",
        "SPONSOR_TECH.md",
        "PREEXISTING.md",
        "LICENSE",
        "requirements.txt",
        "pyproject.toml",
        ".env.example",
        "data/ground_truth.json",
        "scripts/smoke_zetaris.py",
        "scripts/smoke_nightshift.py",
    ]
    missing = [f for f in required if not (ROOT / f).exists()]
    if missing:
        return report("Required Files", "FAIL", f"Missing files: {missing}")
    return report("Required Files", "PASS", f"All {len(required)} core submission files present.")


def check_secrets_and_env_example() -> bool:
    # 1. Check .env is gitignored
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if ".env" not in [line.strip() for line in gitignore.splitlines()]:
        return report("Secret Hygiene", "FAIL", ".env is NOT in .gitignore")

    # 2. Check .env.example
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in env_example.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            v = v.strip()
            if k in ("SAMPLE_MODE", "ZETARIS_HOST", "ZETARIS_PORT"):
                continue
            if not any(token in v for token in ("PLACEHOLDER", "example.com", "localhost")):
                return report("Secret Hygiene", "FAIL", f".env.example has non-placeholder: {k}={v}")

    # 3. Quick working tree regex scan
    secret_regexes = [
        re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"),
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ]
    violations = []
    for p in ROOT.rglob("*.py"):
        if any(ignored in p.parts for ignored in (".git", ".pytest_cache", "__pycache__", "runs")):
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for rgx in secret_regexes:
            if rgx.search(txt):
                violations.append(str(p.relative_to(ROOT)))

    if violations:
        return report("Secret Hygiene", "FAIL", f"Possible secrets in: {violations}")
    return report("Secret Hygiene", "PASS", ".env gitignored, .env.example clean, no active secrets.")


def check_llm_call_sites_and_bypass() -> bool:
    """Verify all LLM calls route through NightshiftLLMClient and detect any bypass."""
    bypass_found = []
    third_party_sdks = ["import openai", "from openai", "import anthropic", "from anthropic"]
    for p in ROOT.rglob("*.py"):
        if any(ignored in p.parts for ignored in (".git", ".pytest_cache", "__pycache__", "venv")):
            continue
        if p.name == "audit.py":
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for sdk in third_party_sdks:
            if sdk in txt:
                bypass_found.append(f"{p.relative_to(ROOT)}: {sdk}")

    if bypass_found:
        return report("LLM Provider Routing", "FAIL", f"Bypass detected: {bypass_found}")

    # Check whether complete_llm is called in agent loop
    agents_dir = ROOT / "src" / "dd" / "agents"
    agent_calls = 0
    for p in agents_dir.glob("*.py"):
        if p.name == "base_agent.py":
            continue
        txt = p.read_text(encoding="utf-8")
        if "complete_llm(" in txt or "llm_client.complete(" in txt:
            agent_calls += 1

    if agent_calls == 0:
        return report(
            "LLM Agent Invocation",
            "FAIL",
            "CRITICAL: complete_llm() is NEVER called in src/dd/agents/ (heuristic bypass).",
        )
    return report("LLM Agent Invocation", "PASS", "Agents call complete_llm() correctly.")


def check_offline_sample_mode() -> bool:
    """Run CLI with --sample to verify offline execution."""
    cmd = [sys.executable, "-m", "src.dd.main", "--profile", "A", "--sample"]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if res.returncode != 0:
        return report("Offline Sample Mode", "FAIL", f"CLI --sample failed:\n{res.stderr[:300]}")
    if "DuckDBDataLayer" not in res.stdout or "ReplayLLMClient" not in res.stdout:
        return report("Offline Sample Mode", "FAIL", "CLI did not use DuckDBDataLayer + ReplayLLMClient.")
    return report("Offline Sample Mode", "PASS", "Sample mode executed successfully with offline adapters.")


def check_trace_model_tagging() -> bool:
    """Verify trace records contain valid model names and identify discrepancies."""
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return report("Trace Audit", "PARTIAL", "No runs directory found.")
    trace_files = list(runs_dir.glob("*/trace.jsonl"))
    if not trace_files:
        return report("Trace Audit", "PARTIAL", "No trace.jsonl files found.")

    latest_trace = max(trace_files, key=lambda f: f.stat().st_mtime)
    lines = latest_trace.read_text(encoding="utf-8").strip().splitlines()

    models_seen = set()
    sub_ms_llm_steps = []
    for line in lines:
        try:
            import json

            data = json.loads(line)
            m = data.get("model")
            if m:
                models_seen.add(m)
            if data.get("agent") in ("red_team", "verifier"):
                lat = data.get("latency_ms", 999)
                prov = data.get("provider", "")
                if lat < 5.0 and "nvidia/nemotron" in str(m).lower() and prov != "sample-stub":
                    sub_ms_llm_steps.append((data.get("agent"), lat))
        except Exception:
            pass

    if sub_ms_llm_steps:
        return report(
            "Trace Audit",
            "FAIL",
            f"Trace fabricates model execution: steps {sub_ms_llm_steps} logged Nemotron with sub-5ms latency without network calls.",
        )
    return report("Trace Audit", "PASS", f"Models logged: {models_seen}")


def check_examples_directory() -> bool:
    examples_dir = ROOT / "examples"
    files = [f.name for f in examples_dir.iterdir() if f.name != ".gitkeep"]
    if not files:
        return report("Examples Coverage", "FAIL", "examples/ is empty (.gitkeep only). At least 3 sample inputs/outputs required.")
    return report("Examples Coverage", "PASS", f"Found {len(files)} sample artifacts in examples/.")


def check_make_and_eval_paths() -> bool:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    if "python eval/run_eval.py" in makefile and not (ROOT / "eval" / "run_eval.py").exists():
        return report("Build Targets", "FAIL", "Makefile line 21 calls missing file 'eval/run_eval.py'.")
    return report("Build Targets", "PASS", "Makefile targets point to valid files.")


def check_requirements_completeness() -> bool:
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "pytz" not in reqs:
        return report("Requirements Check", "FAIL", "'pytz' missing from requirements.txt (breaks DuckDB timestamp parsing on clean install).")
    return report("Requirements Check", "PASS", "Core requirements present.")


def main() -> None:
    print(f"\n{BOLD}{'=' * 75}{RESET}")
    print(f"{BOLD} DIGITAL DOPPELGÄNGER — REPEATABLE COMPLIANCE AUDIT{RESET}")
    print(f"{BOLD}{'=' * 75}{RESET}\n")

    results = [
        check_required_files(),
        check_secrets_and_env_example(),
        check_requirements_completeness(),
        check_make_and_eval_paths(),
        check_examples_directory(),
        check_offline_sample_mode(),
        check_llm_call_sites_and_bypass(),
        check_trace_model_tagging(),
    ]

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n{BOLD}{'=' * 75}{RESET}")
    print(f"Summary: {passed}/{total} automated checks passed.")
    if passed < total:
        print(f"{RED}{BOLD}AUDIT FAILED: Fix blocking issues before submitting!{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}ALL AUTOMATED AUDIT CHECKS PASSED{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
