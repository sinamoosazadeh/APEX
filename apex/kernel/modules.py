"""Module registry and start ordering.

Book II 29.23: dependencies point inward only and cycles are rejected.
The registry computes a deterministic topological start order (stable
alphabetical tie-breaking) so every boot starts modules identically -
and shutdown walks the exact reverse.
"""

from apex.core.contracts.interfaces import IModule
from apex.core.enums import ModuleState
from apex.core.exceptions import KernelError


class ModuleRegistry:
    """Holds kernel modules and derives their deterministic start order."""

    def __init__(self) -> None:
        self._modules: dict[str, IModule] = {}
        self._states: dict[str, ModuleState] = {}

    def register(self, module: IModule) -> None:
        """Register a module by unique name."""
        if module.name in self._modules:
            raise KernelError(
                "module name already registered",
                code="KRN-010",
                details={"module": module.name},
            )
        self._modules[module.name] = module
        self._states[module.name] = ModuleState.REGISTERED

    def get(self, name: str) -> IModule:
        """Return a registered module."""
        if name not in self._modules:
            raise KernelError(
                "module is not registered",
                code="KRN-011",
                details={"module": name},
            )
        return self._modules[name]

    def state_of(self, name: str) -> ModuleState:
        """Current lifecycle state of a module."""
        if name not in self._states:
            raise KernelError(
                "module is not registered",
                code="KRN-011",
                details={"module": name},
            )
        return self._states[name]

    def set_state(self, name: str, state: ModuleState) -> None:
        """Record a module's lifecycle transition."""
        if name not in self._modules:
            raise KernelError(
                "module is not registered",
                code="KRN-011",
                details={"module": name},
            )
        self._states[name] = state

    @property
    def names(self) -> tuple[str, ...]:
        """All registered module names, sorted."""
        return tuple(sorted(self._modules))

    def start_order(self) -> tuple[str, ...]:
        """Deterministic dependency-respecting start order (Kahn).

        Alphabetical tie-breaking keeps the order stable across runs;
        unknown dependencies and cycles are contract violations.
        """
        self._check_dependencies_known()
        remaining_deps: dict[str, set[str]] = {
            name: set(self._modules[name].dependencies) for name in self._modules
        }
        ordered: list[str] = []
        while remaining_deps:
            ready = sorted(name for name, deps in remaining_deps.items() if not deps)
            if not ready:
                cycle_members = ", ".join(sorted(remaining_deps))
                raise KernelError(
                    "circular module dependency detected",
                    code="KRN-012",
                    details={"modules": cycle_members},
                )
            for name in ready:
                ordered.append(name)
                del remaining_deps[name]
            for deps in remaining_deps.values():
                deps.difference_update(ready)
        return tuple(ordered)

    def _check_dependencies_known(self) -> None:
        for name, module in self._modules.items():
            for dependency in module.dependencies:
                if dependency not in self._modules:
                    raise KernelError(
                        "module depends on an unregistered module",
                        code="KRN-013",
                        details={"module": name, "dependency": dependency},
                    )
