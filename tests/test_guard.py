"""Tests for the tool allowlist guard."""

from __future__ import annotations

import pytest

from src.dd.guard.tool_guard import (
    ALLOWED_TOOLS,
    ToolNotAllowedError,
    check_tool_allowed,
    guard_tool_call,
)


class TestCheckToolAllowed:
    """check_tool_allowed returns True/False correctly."""

    @pytest.mark.parametrize("tool", sorted(ALLOWED_TOOLS))
    def test_allowed_tool_passes(self, tool: str) -> None:
        assert check_tool_allowed(tool) is True

    @pytest.mark.parametrize(
        "tool",
        ["web_search", "shell_exec", "file_read", "file_write", "http_get", "eval", "exec"],
    )
    def test_blocked_tool_returns_false(self, tool: str) -> None:
        assert check_tool_allowed(tool) is False


class TestGuardToolCall:
    """guard_tool_call raises on disallowed tools."""

    @pytest.mark.parametrize("tool", sorted(ALLOWED_TOOLS))
    def test_allowed_tool_does_not_raise(self, tool: str) -> None:
        guard_tool_call(tool)  # should not raise

    @pytest.mark.parametrize(
        "tool",
        ["web_search", "shell_exec", "file_read", "file_write", "http_get", "eval", "exec"],
    )
    def test_blocked_tool_raises_error(self, tool: str) -> None:
        with pytest.raises(ToolNotAllowedError) as exc_info:
            guard_tool_call(tool)
        assert tool in str(exc_info.value)

    def test_error_message_contains_allowlist(self) -> None:
        with pytest.raises(ToolNotAllowedError) as exc_info:
            guard_tool_call("web_search")
        msg = str(exc_info.value)
        for allowed in ALLOWED_TOOLS:
            assert allowed in msg
