"""Plugin contract (Book II 3.23, 5.19).

Every extension - indicators, features, strategies, exchange
connectors - enters the platform through this single contract. A
plugin declares a manifest, builds its kernel modules against injected
services, and never reaches into Core internals.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from apex.core.contracts.interfaces import IModule
from apex.core.enums import PluginKind, StabilityLevel
from apex.core.exceptions import ValidationError
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer

# The plugin API version this platform build speaks (Book II 5.26).
PLUGIN_API_VERSION = SemanticVersion(1, 0, 0)


@dataclass(frozen=True, slots=True, kw_only=True)
class PluginManifest:
    """Self-description a plugin must publish (Book II 29.24)."""

    name: str
    version: SemanticVersion
    kind: PluginKind
    api_version: SemanticVersion
    description: str
    stability: StabilityLevel = StabilityLevel.EXPERIMENTAL
    requires: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.lower():
            raise ValidationError(
                "plugin name must be non-empty lowercase",
                code="VAL-120",
                details={"name": self.name},
            )
        if not self.description:
            raise ValidationError("plugin description must not be empty", code="VAL-121")


@runtime_checkable
class IPlugin(Protocol):
    """The single interface every plugin implements (Book II 5.19)."""

    @property
    def manifest(self) -> PluginManifest:
        """The plugin's self-description."""
        ...

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the plugin's kernel modules from injected services.

        Plugins receive dependencies through the container - they never
        construct platform services themselves (Constitution 3.8) and
        never mutate Core (Book II 5.19).
        """
        ...
