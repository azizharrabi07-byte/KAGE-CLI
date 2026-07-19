"""KAGE OS — a personal AI operating system for the terminal (Termux).

This package is CLI-only. There is no web server and no HTML interface.
All interaction happens through the `kage` command (a REPL with slash
commands) and, optionally, the Discord/Telegram transport agents.

Public entry point: ``kage.kage:main`` (registered as the ``kage`` script).
"""

__version__ = "3.0.0"
__all__ = ["__version__"]
