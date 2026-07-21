"""Plugin loader (Book II 29.24).

At startup, configured plugins are imported, their manifests are
validated (structure, API version compatibility, duplicate names,
dependency closure), and their kernel modules are registered. A
failing plugin aborts boot - the platform never runs half-loaded.

Cryptographic signature verification of plugin artifacts is owned by
the Security Platform (Phase 13); until then the loader validates
everything that can be validated without a trust infrastructure.
"""

import importlib
from dataclasses import dataclass

from apex.core.exceptions import ApexError, KernelError
from apex.core.logging import StructuredLogger
from apex.kernel.container import ServiceContainer
from apex.kernel.modules import ModuleRegistry
from apex.plugins.contract import PLUGIN_API_VERSION, IPlugin, PluginManifest

# A plugin module must expose this attribute holding its IPlugin object.
PLUGIN_ATTRIBUTE = "APEX_PLUGIN"


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadedPlugin:
    """Record of one successfully loaded plugin."""

    manifest: PluginManifest
    module_path: str
    module_names: tuple[str, ...]


class PluginLoader:
    """Imports, validates and registers configured plugins."""

    def __init__(
        self,
        *,
        container: ServiceContainer,
        registry: ModuleRegistry,
        logger: StructuredLogger,
    ) -> None:
        self._container = container
        self._registry = registry
        self._logger = logger
        self._loaded: dict[str, LoadedPlugin] = {}

    @property
    def loaded(self) -> tuple[LoadedPlugin, ...]:
        """Successfully loaded plugins, in load order."""
        return tuple(self._loaded.values())

    def load_all(self, module_paths: tuple[str, ...]) -> tuple[LoadedPlugin, ...]:
        """Load every configured plugin; abort on the first violation."""
        for module_path in module_paths:
            self._load_one(module_path)
        self._check_dependencies()
        return self.loaded

    def _load_one(self, module_path: str) -> None:
        plugin = self._import_plugin(module_path)
        manifest = plugin.manifest
        self._validate_manifest(manifest, module_path)
        modules = plugin.build_modules(self._container)
        module_names = []
        for module in modules:
            self._registry.register(module)
            module_names.append(module.name)
        self._loaded[manifest.name] = LoadedPlugin(
            manifest=manifest,
            module_path=module_path,
            module_names=tuple(module_names),
        )
        self._logger.info(
            "plugin_loaded",
            plugin=manifest.name,
            version=str(manifest.version),
            kind=manifest.kind.value,
            modules=", ".join(module_names),
        )

    def _import_plugin(self, module_path: str) -> IPlugin:
        try:
            module = importlib.import_module(module_path)
        except ImportError as error:
            raise KernelError(
                "plugin module could not be imported",
                code="KRN-040",
                details={"module_path": module_path, "reason": str(error)},
            ) from error
        candidate = getattr(module, PLUGIN_ATTRIBUTE, None)
        if candidate is None:
            raise KernelError(
                f"plugin module does not expose {PLUGIN_ATTRIBUTE}",
                code="KRN-041",
                details={"module_path": module_path},
            )
        if not isinstance(candidate, IPlugin):
            raise KernelError(
                "plugin object does not satisfy the IPlugin contract",
                code="KRN-042",
                details={"module_path": module_path},
            )
        return candidate

    def _validate_manifest(self, manifest: PluginManifest, module_path: str) -> None:
        if manifest.name in self._loaded:
            raise KernelError(
                "duplicate plugin name",
                code="KRN-043",
                details={"plugin": manifest.name, "module_path": module_path},
            )
        if not manifest.api_version.is_compatible_with(PLUGIN_API_VERSION):
            raise KernelError(
                "plugin API version is incompatible with this platform",
                code="KRN-044",
                details={
                    "plugin": manifest.name,
                    "plugin_api": str(manifest.api_version),
                    "platform_api": str(PLUGIN_API_VERSION),
                },
            )

    def _check_dependencies(self) -> None:
        for record in self._loaded.values():
            for requirement in record.manifest.requires:
                if requirement not in self._loaded:
                    raise KernelError(
                        "plugin requires a plugin that is not loaded",
                        code="KRN-045",
                        details={
                            "plugin": record.manifest.name,
                            "requires": requirement,
                        },
                    )


def safe_load(
    loader: PluginLoader,
    module_paths: tuple[str, ...],
) -> tuple[LoadedPlugin, ...]:
    """Load plugins, wrapping unexpected errors in the kernel contract."""
    try:
        return loader.load_all(module_paths)
    except ApexError:
        raise
    except Exception as error:
        raise KernelError(
            "unexpected failure while loading plugins",
            code="KRN-046",
            details={"reason": str(error), "exception": type(error).__name__},
        ) from error
