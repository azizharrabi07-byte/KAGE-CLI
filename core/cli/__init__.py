"""
KAGE OS Production CLI Package.
Provides output formatters, tab-completion, setup wizard, and flag-based command runners.
"""

from .formatter import TableFormatter, OutputFormatter, Spinner
from .autocomplete import CLICompleter
from .wizard import ConfigWizard
from .runner import ExecutionFlags, CommandRunner

__all__ = [
    "TableFormatter",
    "OutputFormatter",
    "Spinner",
    "CLICompleter",
    "ConfigWizard",
    "ExecutionFlags",
    "CommandRunner",
]
