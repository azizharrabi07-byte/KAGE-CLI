"""Security hardening tests: paths, text, shell args, secrets, sandbox."""

from __future__ import annotations
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.core import secrets as secrets_mod
from kage.core import sandbox
from kage.core.security import (escape_shell_arg, restrict_to_sandbox, sanitize_path,
    sanitize_text, sandbox_path, validate_shell)

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_path_sanitization():
    check("basic", sanitize_path("notes/a.md") == "notes/a.md")
    check("strip slash", sanitize_path("/etc/x") == "etc/x")
    check("sanitize backslash to slash", sanitize_path(chr(65) + chr(92) + "b") == "A/b")

def test_path_traversal_blocked():
    for bad in ("../../etc/passwd", "..", "a/../../../b"):
        try: sanitize_path(bad); check(f"block {bad}", False)
        except ValueError: check(f"block {bad}", True)

def test_null_byte():
    try: sanitize_path("a\x00b"); check("null byte", False)
    except ValueError: check("null byte", True)

def test_text_sanitization():
    check("control", sanitize_text("a\x00b\x07c") == "abc")
    check("CR", sanitize_text("a\r\nb") == "a\nb")
    check("cap", len(sanitize_text("x"*100, max_len=10)) == 10)

def test_shell_escape():
    check("quote", escape_shell_arg("it's") == "'it'\"'\"'s'")
    check("plain", escape_shell_arg("hello") == "'hello'")

def test_restrict_to_sandbox():
    root = tempfile.mkdtemp(prefix="kage-sb-")
    r = restrict_to_sandbox(root, "deep/file.md", create=True)
    check("inside", str(r).startswith(root))
    try: restrict_to_sandbox(root, "../escape"); check("escape", False)
    except ValueError: check("escape", True)

def test_legacy_sandbox_path():
    root = tempfile.mkdtemp(prefix="kage-sp-")
    p = sandbox_path(root, "ok.txt")
    check("legacy ok", str(p).startswith(root))
    try: sandbox_path(root, "../../bad"); check("legacy traversal", False)
    except ValueError: check("legacy traversal", True)

def test_validate_shell():
    for bad in ("rm -rf /", "ls; rm x", "echo $(whoami)", "echo `id`"):
        try: validate_shell(bad); check(f"block {bad}", False)
        except ValueError: check(f"block {bad}", True)

def test_sandbox_module():
    res = sandbox.validate_command("ls -la"); check("allow ls", res.ok)
    res = sandbox.run("echo hi", dry_run=True); check("dry run", res.ok and res.data["executed"] is False)
    res = sandbox.run("rm -rf /"); check("block rm", res.ok is False)
    res = sandbox.validate_command("cat /etc/passwd"); check("block abs read", res.ok is False)

def test_secrets():
    secrets_mod.add_secret("TEST_SEC", "sk-1234567890abcdef")
    check("resolve", secrets_mod.resolve("TEST_SEC") == "sk-1234567890abcdef")
    m = secrets_mod.mask("sk-1234567890abcdef")
    check("masked", m.endswith("cdef") and "1234567890" not in m)
    check("scrub", "REDACTED" in secrets_mod.scrub("api_key=abcdefgh1234 done"))
    check("removed", secrets_mod.remove_secret("TEST_SEC") is True)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nSecurity tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
