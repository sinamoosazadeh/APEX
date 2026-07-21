"""Dependency injection container.

Constitution 3.8: no class constructs its own dependencies - even the
logger, configuration and clock are injected. The container is
deliberately explicit: services are registered by type, resolution is
eager-checked, factories are memoized as singletons, and circular
factory chains are detected and rejected.
"""

from collections.abc import Callable
from typing import TypeVar, cast

from apex.core.exceptions import KernelError

_T = TypeVar("_T")

type ServiceFactory[T] = Callable[["ServiceContainer"], T]


class ServiceContainer:
    """Explicit, type-keyed service registry."""

    def __init__(self) -> None:
        self._instances: dict[type, object] = {}
        self._factories: dict[type, ServiceFactory[object]] = {}
        self._resolving: list[type] = []

    def register_instance(self, service_type: type[_T], instance: _T) -> None:
        """Register an already-built singleton."""
        self._ensure_unregistered(service_type)
        self._instances[service_type] = instance

    def register_factory(
        self,
        service_type: type[_T],
        factory: ServiceFactory[_T],
    ) -> None:
        """Register a lazily-built singleton factory."""
        self._ensure_unregistered(service_type)
        self._factories[service_type] = cast(ServiceFactory[object], factory)

    def resolve(self, service_type: type[_T]) -> _T:
        """Return the singleton for ``service_type``, building if lazy."""
        if service_type in self._instances:
            return cast(_T, self._instances[service_type])
        if service_type not in self._factories:
            raise KernelError(
                "service is not registered",
                code="KRN-001",
                details={"service": service_type.__name__},
            )
        if service_type in self._resolving:
            chain = " -> ".join(t.__name__ for t in self._resolving)
            raise KernelError(
                "circular dependency detected during resolution",
                code="KRN-002",
                details={"chain": f"{chain} -> {service_type.__name__}"},
            )
        self._resolving.append(service_type)
        try:
            instance = self._factories[service_type](self)
        finally:
            self._resolving.pop()
        self._instances[service_type] = instance
        return cast(_T, instance)

    def contains(self, service_type: type) -> bool:
        """Whether a service is registered (built or lazy)."""
        return service_type in self._instances or service_type in self._factories

    def registered_types(self) -> tuple[str, ...]:
        """Names of all registered service types (deterministic order)."""
        names = {t.__name__ for t in self._instances} | {t.__name__ for t in self._factories}
        return tuple(sorted(names))

    def _ensure_unregistered(self, service_type: type) -> None:
        if self.contains(service_type):
            raise KernelError(
                "service is already registered",
                code="KRN-003",
                details={"service": service_type.__name__},
            )
