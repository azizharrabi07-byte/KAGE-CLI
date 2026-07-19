"""Integration tests for BaseIntegration, Obsidian, WhatsApp (HTTP mocked)."""

from __future__ import annotations
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.core.integrations.obsidian import ObsidianIntegration
from kage.core.integrations.whatsapp import WhatsAppIntegration
from kage.core.integrations.base_integration import BaseIntegration
from kage.core.result import ToolResult

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

def make_urlopen_mock(responder):
    def _urlopen(req, timeout=None, context=None):
        raw, _ = responder(req.get_method(), req.full_url, req.data)
        return FakeResponse(raw if isinstance(raw, bytes) else raw.encode())
    return _urlopen

def _patch(responder):
    import urllib.request as ur
    orig = ur.urlopen; ur.urlopen = make_urlopen_mock(responder)
    return lambda: setattr(ur, "urlopen", orig)

def test_obsidian_missing_token():
    os.environ.pop("OBSIDIAN_TOKEN", None)
    o = ObsidianIntegration()
    check("obsidian no token", o.connect().ok is False)

def test_obsidian_round_trip():
    os.environ["OBSIDIAN_TOKEN"] = "secret"; calls = {}
    def responder(method, url, body):
        calls["method"] = method
        if method == "GET" and url.endswith("/vault/"):
            return json.dumps({"files": [{"path": "a.md"}, {"path": "b.md"}]}), 200
        if method == "GET" and "/vault/a.md" in url: return "# Hello", 200
        if method == "PUT": calls["body"] = body; return "", 204
        if "/search/simple/" in url: return json.dumps([{"path": "a.md"}]), 200
        return json.dumps({"vault": "Mine"}), 200
    restore = _patch(responder)
    try:
        o = ObsidianIntegration(retries=1, base_delay=0)
        check("obsidian connect", o.connect().ok is True)
        check("obsidian list", o.list_files() == ["a.md", "b.md"])
        check("obsidian read", o.read_file("a.md") == "# Hello")
        o.send({"path": "c.md", "content": "new"})
        check("obsidian write PUT", calls.get("method") == "PUT")
        check("obsidian search", isinstance(o.search("hi"), list))
        check("obsidian health", o.health_check().ok is True)
    finally: restore(); os.environ.pop("OBSIDIAN_TOKEN", None)

def test_whatsapp_missing_bridge():
    w = WhatsAppIntegration(retries=1, base_delay=0)
    check("whatsapp no bridge", w.connect().ok is False)

def test_whatsapp_send():
    os.environ["WHATSAPP_BRIDGE_TOKEN"] = "tok"; sent = {}
    def responder(method, url, body):
        if url.endswith("/health"): return json.dumps({"authenticated": True}), 200
        if url.endswith("/send"): sent["body"] = json.loads(body.decode()); return json.dumps({"id": "m_1"}), 200
        return json.dumps({}), 200
    restore = _patch(responder)
    try:
        w = WhatsAppIntegration(retries=1, base_delay=0)
        check("whatsapp connect", w.connect().ok is True)
        res = w.send({"to": "1234", "text": "hi"})
        check("whatsapp send ok", res.ok is True)
        check("whatsapp payload", sent.get("body", {}).get("to") == "1234")
        check("whatsapp health", w.health_check().ok is True)
    finally: restore(); os.environ.pop("WHATSAPP_BRIDGE_TOKEN", None)

def test_whatsapp_send_missing_args():
    w = WhatsAppIntegration(retries=1, base_delay=0); w._connected = True
    res = w.send({"to": "", "text": ""})
    check("whatsapp missing args", res.ok is False)

def test_base_contract():
    class Dummy(BaseIntegration):
        name = kind = "dummy"
        def connect(self): self._connected = True; return ToolResult.success({"connected": True})
        def _send(self, payload): return {"sent": payload}
        def _receive(self, payload): return [{"in": 1}]
    d = Dummy(retries=2, base_delay=0)
    check("dummy connect", d.connect().ok is True)
    check("dummy health", d.health_check().ok is True)
    s = d.send({"x": 1}); check("dummy send", s.ok and s.data == {"sent": {"x": 1}})
    r = d.receive(); check("dummy receive", r.ok and r.data == [{"in": 1}])
    check("dummy disconnect", d.disconnect().ok is True and d.connected is False)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nIntegration tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
