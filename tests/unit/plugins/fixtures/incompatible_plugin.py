"""A plugin declaring an incompatible API major version."""

from collections.abc import Sequence

from apex.core.contracts.interfaces import IModule
from apex.core.enums import PluginKind
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest


class IncompatiblePlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="incompatible_plugin",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(2, 0, 0),  # platform speaks 1.x
            description="test fixture with wrong api version",
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        return []


APEX_PLUGIN = IncompatiblePlugin()
