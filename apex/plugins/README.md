# apex.plugins — Plugin System

Book II 3.23 / 5.19 / 29.24. Every extension enters through one
contract: `PluginManifest` (name, version, kind, API version,
dependencies, stability) + `IPlugin.build_modules(container)`. The
`PluginLoader` imports configured modules, validates API compatibility,
duplicates and dependency closure, and registers kernel modules; any
violation aborts boot. Cryptographic artifact signatures arrive with
the Security Platform (Phase 13).

Tests: `tests/unit/plugins/`.
