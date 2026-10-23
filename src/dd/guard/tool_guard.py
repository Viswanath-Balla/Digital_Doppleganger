"""Tool allowlist guard.

Agents may ONLY call tools in the ALLOWED_TOOLS set.
This prevents arbitrary code execution, web access, file-system access, etc.
"""

from __future__ import annotations


class ToolNotAllowedError(Exception):
    """Raised when an agent tries to use a tool not in the allowlist."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(
            f"Tool '{tool_name}' is not in the allowlist. "
            f"Allowed tools: {sorted(ALLOWED_TOOLS)}"
        )


# The ONLY tools agents are permitted to invoke.
ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "sql_query",          # DataLayer.query
        "llm_complete",       # LLMClient.complete
        "world_model_read",   # WorldModel.get / query_entities / evidence_chain
        "world_model_write",  # WorldModel.ingest / link
    }
)


def check_tool_allowed(tool_name: str) -> bool:
    """Return True if *tool_name* is in the allowlist."""
    return tool_name in ALLOWED_TOOLS


def guard_tool_call(tool_name: str) -> None:
    """Raise ToolNotAllowedError if *tool_name* is not allowlisted.

    Call this at the entry point of every agent tool dispatch.
    """
    if tool_name not in ALLOWED_TOOLS:
        raise ToolNotAllowedError(tool_name)
