"""core/ipc.py — Unix domain socket protocol between the CLI and the daemon.

The daemon (``kage start``) owns the supervisor + agents and listens on a
socket. The CLI (and transports) send newline-delimited JSON requests and read
one JSON response. This keeps one warm process for fast responses on Termux.

Protocol (one JSON object per line):
    -> {"type": "chat", "user_id": "...", "message": "..."}
    <- {"ok": true, "response": {...}}
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

log = logging.getLogger("kage.ipc")


def _ensure_dir(socket_path: str) -> str:
    p = os.path.expanduser(socket_path)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    return p


class IPCServer:
    """Accepts JSON-line requests; dispatches via a handler callback."""

    def __init__(self, socket_path: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.socket_path = _ensure_dir(socket_path)
        self.handler = handler
        self._sock: Optional[socket.socket] = None
        self._running = False

    def serve_forever(self) -> None:
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self.socket_path)
        self._sock.listen(16)
        os.chmod(self.socket_path, 0o600)
        self._running = True
        log.info("IPC server listening on %s", self.socket_path)
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            buf = b""
            try:
                while self._running:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if not line.strip():
                            continue
                        reply = self._dispatch(line)
                        conn.sendall((json.dumps(reply) + "\n").encode())
            except Exception as exc:  # noqa: BLE001
                log.warning("ipc client error: %s", exc)

    def _dispatch(self, line: bytes) -> Dict[str, Any]:
        try:
            req = json.loads(line.decode())
            return self.handler(req)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            finally:
                if os.path.exists(self.socket_path):
                    os.unlink(self.socket_path)


class IPCClient:
    """Thin client used by the CLI to talk to the running daemon."""

    def __init__(self, socket_path: str, timeout: float = 30.0) -> None:
        self.socket_path = os.path.expanduser(socket_path)
        self.timeout = timeout

    def is_alive(self) -> bool:
        return os.path.exists(self.socket_path)

    def request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_alive():
            return {"ok": False, "error": "daemon not running (try `kage start`)"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect(self.socket_path)
            s.sendall((json.dumps(payload) + "\n").encode())
            data = s.recv(65536)
        try:
            return json.loads(data.decode())
        except json.JSONDecodeError:
            return {"ok": False, "error": "malformed daemon response"}
