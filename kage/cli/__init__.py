"""kage.cli — production command-line interface (Phase 3).

Interactive REPL with slash commands plus batch modes (--json/--yaml) and
dry-run (--dry-run). All commands here rely only on stdlib-backed core modules
so the CLI works even without network/transport dependencies installed.
"""

from .repl import REPL, run_command, main  # noqa: F401

__all__ = ["REPL", "run_command", "main"]
