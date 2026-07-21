"""Feature registry (Book II 29.10: registry before store and pipeline).

Every feature the platform can compute is declared here before any
value is produced. Engines may only emit names they registered - the
pipeline enforces it - so the feature universe is always explicit,
versioned and auditable.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from apex.core.exceptions import FeatureError
from apex.core.validation import ensure_not_empty
from apex.core.versioning import SemanticVersion

type FeatureParamValue = float | int | bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureDefinition:
    """Declaration of one computable feature."""

    name: str
    family: str
    description: str
    version: SemanticVersion
    default_params: Mapping[str, FeatureParamValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ensure_not_empty(self.name, "name")
        ensure_not_empty(self.family, "family")
        ensure_not_empty(self.description, "description")
        if not self.name.startswith(f"{self.family}."):
            raise FeatureError(
                "feature name must be namespaced by its family",
                code="FEA-001",
                details={"name": self.name, "family": self.family},
            )


class FeatureRegistry:
    """Explicit catalog of every declared feature."""

    def __init__(self) -> None:
        self._definitions: dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        """Declare a feature; duplicate names are contract violations."""
        if definition.name in self._definitions:
            raise FeatureError(
                "feature name already registered",
                code="FEA-002",
                details={"name": definition.name},
            )
        self._definitions[definition.name] = definition

    def register_all(self, definitions: tuple[FeatureDefinition, ...]) -> None:
        """Declare a batch of features."""
        for definition in definitions:
            self.register(definition)

    def get(self, name: str) -> FeatureDefinition:
        """Look up a declared feature."""
        if name not in self._definitions:
            raise FeatureError(
                "feature is not registered",
                code="FEA-003",
                details={"name": name},
            )
        return self._definitions[name]

    def is_registered(self, name: str) -> bool:
        """Whether a feature name is declared."""
        return name in self._definitions

    @property
    def names(self) -> tuple[str, ...]:
        """All declared feature names, sorted."""
        return tuple(sorted(self._definitions))

    @property
    def families(self) -> tuple[str, ...]:
        """All families with at least one declared feature, sorted."""
        return tuple(sorted({d.family for d in self._definitions.values()}))
