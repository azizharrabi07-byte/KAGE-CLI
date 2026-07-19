"""Tests for the tools framework (validation, structured output).

Run:  python -m kage.tests.test_tools
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.tools.base import ToolRegistry  # noqa: E402
from kage.core.tools.browser import WebFetchTool, WebSearchTool  # noqa: E402
from kage.core.tools.shell import ShellTool  # noqa: E402
from kage.core.security import validate_shell  # noqa: E402


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(WebSearchTool())
    reg.register(ShellTool())
    return reg


def test_registry_validation() -> None:
    reg = _registry()
    res = reg.run("web.search", {})  # missing required 'query'
    assert res["ok"] is False
    assert "query" in res["error"]


def test_shell_validation_blocks_destructive() -> None:
    try:
        validate_shell("rm -rf /")
        assert False, "should have blocked rm"
    except ValueError:
        pass


def test_shell_tool_missing_command() -> None:
    reg = _registry()
    res = reg.run("shell.run", {})
    assert res["ok"] is False


def test_search_structured_without_key() -> None:
    reg = _registry()
    os.environ.pop("WEB_SEARCH_API_KEY", None)
    res = reg.run("web.search", {"query": "ai news"})
    assert res["ok"] is True
    assert "note" in res  # graceful "needs provider" structure


def _run_all() -> int:
    import inspect
    failures = 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ERROR {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
