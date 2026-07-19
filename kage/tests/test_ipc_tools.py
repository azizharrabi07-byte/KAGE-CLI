"""Tests for IPC socket round-trip + tool wrappers (shell, browser)."""

from __future__ import annotations
import os, sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.core.ipc import IPCClient, IPCServer
from kage.core.tools.base import ToolRegistry
from kage.core.tools.browser import WebFetchTool, WebSearchTool
from kage.core.tools.shell import ShellTool

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_ipc_round_trip():
    sock = str(Path(tempfile.mkdtemp()) / "kage.sock")
    server = IPCServer(sock, lambda req: {"ok": True, "echo": req.get("type")})
    t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        time.sleep(0.2); client = IPCClient(sock, timeout=5.0)
        check("ipc alive", client.is_alive() is True)
        res = client.request({"type": "ping"})
        check("ipc roundtrip", res.get("ok") is True and res.get("echo") == "ping")
    finally: server.stop(); time.sleep(0.1)

def test_ipc_unknown():
    sock = str(Path(tempfile.mkdtemp()) / "kage2.sock")
    server = IPCServer(sock, lambda req: {"ok": False, "error": "unknown"})
    t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        time.sleep(0.2); client = IPCClient(sock, timeout=5.0)
        res = client.request({"type": "bogus"})
        check("ipc error", res.get("ok") is False)
    finally: server.stop(); time.sleep(0.1)

def test_shell_runs():
    reg = ToolRegistry(); reg.register(ShellTool())
    res = reg.run("shell.run", {"command": "echo ipc-tools-test"})
    check("shell echo", res["ok"] and "ipc-tools-test" in res.get("stdout", ""))

def test_shell_blocks():
    reg = ToolRegistry(); reg.register(ShellTool())
    check("shell rm blocked", reg.run("shell.run", {"command": "rm -rf /"})["ok"] is False)

def test_browser_fetch():
    res = WebFetchTool().run({"url": "http://127.0.0.1:1/never"})
    check("fetch structured", "ok" in res and (res["ok"] is False or "snippet" in res))

def test_browser_search():
    os.environ.pop("WEB_SEARCH_API_KEY", None)
    res = WebSearchTool().run({"query": "ai news"})
    check("search graceful", res["ok"] is True and "note" in res)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nIPC + tool tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
