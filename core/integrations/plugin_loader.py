#!/usr/bin/env python3
"""
plugin_loader.py — Dynamic Integration Plugin Loader for KAGE OS.
Scans plugin directories, loads custom python modules, and registers custom integrations and agents.
"""

import importlib.util
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .registry import ProviderRegistry

logger = logging.getLogger("kage.plugins")


class PluginLoader:
    """Discovers and loads third-party plugins and dynamic agents from specified directories."""

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs = plugin_dirs or [
            Path.home() / ".kage" / "plugins",
            Path(__file__).parent.parent.parent / "plugins"
        ]

    def discover_and_load(self) -> List[str]:
        """Scans plugin directories and imports valid integration plugin modules."""
        loaded_plugins = []
        for p_dir in self.plugin_dirs:
            if not p_dir.exists() or not p_dir.is_dir():
                continue

            for plugin_file in p_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                module_name = f"kage_plugin_{plugin_file.stem}"
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(plugin_file))
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)

                        # Trigger optional plugin entrypoint hook
                        if hasattr(mod, "register_plugin"):
                            mod.register_plugin(ProviderRegistry)

                        loaded_plugins.append(plugin_file.stem)
                        logger.info(f"Successfully loaded integration plugin: '{plugin_file.name}'")
                except Exception as e:
                    logger.error(f"Failed loading plugin '{plugin_file.name}': {e}")

        return loaded_plugins
