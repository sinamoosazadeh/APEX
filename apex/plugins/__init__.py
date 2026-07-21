"""APEX Plugin System (Book II 3.23, 5.19, 29.24).

Every extension enters through one contract: a plugin publishes a
:class:`PluginManifest`, implements :class:`IPlugin` and builds kernel
modules from injected services. The :class:`PluginLoader` imports,
validates (API version, duplicates, dependency closure) and registers
configured plugins at boot; a failing plugin aborts boot.
"""

from apex.plugins.contract import PLUGIN_API_VERSION, IPlugin, PluginManifest
from apex.plugins.loader import LoadedPlugin, PluginLoader, safe_load

__all__ = [
    "PLUGIN_API_VERSION",
    "IPlugin",
    "LoadedPlugin",
    "PluginLoader",
    "PluginManifest",
    "safe_load",
]
