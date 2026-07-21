"""A well-formed test plugin."""

from collections.abc import Sequence

from apex.core.contracts.interfaces import IModule
from apex.core.enums import HealthState, PluginKind
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest


class MarkerService:
    """Registered by the plugin so tests can observe container wiring."""

    def __init__(self, label: str) -> None:
        self.label = label


class NoopModule:
    """Minimal real module."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.started = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ()

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    def health(self) -> HealthState:
        return HealthState.HEALTHY


class GoodPlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="good_plugin",
            version=SemanticVersion(1, 2, 3),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="test fixture plugin",
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        container.register_instance(MarkerService, MarkerService("wired-by-plugin"))
        return [NoopModule("good_module")]


APEX_PLUGIN = GoodPlugin()
