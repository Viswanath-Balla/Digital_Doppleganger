"""Automated tests for Phase 1 & Phase 2: Prompt Loader, Prompt Markdown Files, and Trace Metadata."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.agents.prompt_loader import (
    PROMPTS_DIR,
    clear_prompt_cache,
    get_prompt,
)
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator


class TestPromptLoader:
    """Validate prompt loading, caching, version parsing, and error handling."""

    def setup_method(self) -> None:
        clear_prompt_cache()

    def test_load_valid_planner_prompt(self) -> None:
        prompt = get_prompt("planner")
        assert prompt.agent_name == "planner"
        assert prompt.file_name == "planner.md"
        assert prompt.version == "1.0"
        assert len(prompt.sha256) == 64
        assert "## Role" in prompt.content
        assert "## Rules" in prompt.content
        assert str(prompt) == prompt.content

    def test_load_valid_extractor_and_linker_prompts(self) -> None:
        extractor_p = get_prompt("extractor")
        assert extractor_p.file_name == "extractor.md"
        assert extractor_p.version == "1.0"

        linker_p = get_prompt("linker")
        assert linker_p.file_name == "linker.md"
        assert linker_p.version == "1.0"
        assert "LINKER_GPS_RADIUS_METERS" in linker_p.content
        assert "LINKER_TIME_WINDOW_MINUTES" in linker_p.content

    def test_reject_missing_prompt_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            get_prompt("non_existent_agent", prompts_dir=tmp_path)

    def test_reject_malformed_missing_version(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "planner.md"
        bad_file.write_text(
            "# planner.md\n## Role\nSome role\n## Inputs\ninputs\n## Output schema\nschema\n## Rules\nrules\n## Stop / fail conditions\nstop\n## Tools allowed\ntools\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="version:"):
            get_prompt("planner", prompts_dir=tmp_path)

    def test_reject_malformed_missing_required_section(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "planner.md"
        # Omit '## Output schema'
        bad_file.write_text(
            "# planner.md\nversion: 1.0\n## Role\nSome role\n## Inputs\ninputs\n## Rules\nrules\n## Stop / fail conditions\nstop\n## Tools allowed\ntools\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required section: '## Output schema'"):
            get_prompt("planner", prompts_dir=tmp_path)


class TestPromptTraceIntegration:
    """Verify trace records include prompt_file, prompt_version, prompt_sha256, and model names."""

    def test_trace_contains_prompt_fields_and_link_reasons(self) -> None:
        settings = get_settings()
        data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
        world_model = MeterlessWorldModel()
        llm_client = ReplayLLMClient()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
            max_rounds=2,
        )

        result = asyncio.run(orchestrator.run(profile_id="A"))
        trace_path = Path(result["trace_file"])
        assert trace_path.exists()

        records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").strip().splitlines()]
        assert len(records) >= 5

        # Verify prompt metadata fields on every trace record
        for r in records:
            assert "prompt_file" in r
            assert "prompt_version" in r
            assert "prompt_sha256" in r
            assert "model" in r
            if r["agent"] in ("planner", "extractor", "linker", "red_team", "verifier"):
                assert r["prompt_file"] is not None
                assert r["prompt_version"] == "1.0"
                assert len(r["prompt_sha256"]) == 64

        # Verify link reasons appear in trace details
        linker_records = [r for r in records if r["agent"] == "linker"]
        assert len(linker_records) > 0
        linker_details = linker_records[0].get("details", {})
        assert "link_reasons" in linker_details
        assert len(linker_details["link_reasons"]) >= 2
        reason_codes = {lr.get("reason_code") for lr in linker_details["link_reasons"]}
        assert "gps_distance_cluster" in reason_codes
        assert "shared_identifier" in reason_codes

        # Verify link reasons appear in World Model edge metadata
        edges = world_model.get_edges()
        metadata_reasons = [e.get("metadata", {}).get("reason") for e in edges if e.get("metadata")]
        assert "gps_distance_cluster" in metadata_reasons
        assert "shared_identifier" in metadata_reasons
