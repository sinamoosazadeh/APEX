"""A plugin that requires another plugin to be loaded."""

from collections.abc import Sequence

from apex.core.contracts.interfaces import IModule
from apex.core.enums import PluginKind
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest


class NeedyPlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="needy_plugin",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="test fixture requiring good_plugin",
            requires=("good_plugin",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        return []


APEX_PLUGIN = NeedyPlugin()
