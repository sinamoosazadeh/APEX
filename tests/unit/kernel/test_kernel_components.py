"""Kernel components: container, module registry, health monitor."""

import pytest
from apex.core.enums import HealthState
from apex.core.exceptions import KernelError
from apex.core.time.clock import ManualClock
from apex.kernel.container import ServiceContainer
from apex.kernel.health import HealthMonitor
from apex.kernel.modules import ModuleRegistry

from tests.conftest import T0


class Greeter:
    def __init__(self, name: str = "apex") -> None:
        self.name = name


class Consumer:
    def __init__(self, greeter: Greeter) -> None:
        self.greeter = greeter


class FakeModule:
    def __init__(self, name: str, dependencies: tuple[str, ...] = ()) -> None:
        self._name = name
        self._dependencies = dependencies
        self.started = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self._dependencies

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    def health(self) -> HealthState:
        return HealthState.HEALTHY


class TestServiceContainer:
    def test_register_and_resolve_instance(self) -> None:
        container = ServiceContainer()
        container.register_instance(Greeter, Greeter("core"))
        assert container.resolve(Greeter).name == "core"

    def test_factory_is_memoized(self) -> None:
        container = ServiceContainer()
        container.register_factory(Greeter, lambda c: Greeter())
        assert container.resolve(Greeter) is container.resolve(Greeter)

    def test_factory_composition(self) -> None:
        container = ServiceContainer()
        container.register_factory(Greeter, lambda c: Greeter("wired"))
        container.register_factory(Consumer, lambda c: Consumer(c.resolve(Greeter)))
        assert container.resolve(Consumer).greeter.name == "wired"

    def test_duplicate_registration_rejected(self) -> None:
        container = ServiceContainer()
        container.register_instance(Greeter, Greeter())
        with pytest.raises(KernelError) as excinfo:
            container.register_factory(Greeter, lambda c: Greeter())
        assert excinfo.value.code == "KRN-003"

    def test_unregistered_resolution_rejected(self) -> None:
        with pytest.raises(KernelError) as excinfo:
            ServiceContainer().resolve(Greeter)
        assert excinfo.value.code == "KRN-001"

    def test_circular_factories_detected(self) -> None:
        container = ServiceContainer()
        container.register_factory(Greeter, lambda c: Greeter(c.resolve(Consumer).greeter.name))
        container.register_factory(Consumer, lambda c: Consumer(c.resolve(Greeter)))
        with pytest.raises(KernelError) as excinfo:
            container.resolve(Greeter)
        assert excinfo.value.code == "KRN-002"


class TestModuleRegistry:
    def test_start_order_respects_dependencies(self) -> None:
        registry = ModuleRegistry()
        registry.register(FakeModule("storage", ("events",)))
        registry.register(FakeModule("events"))
        registry.register(FakeModule("market", ("storage", "events")))
        assert registry.start_order() == ("events", "storage", "market")

    def test_start_order_is_deterministic_alphabetical(self) -> None:
        registry = ModuleRegistry()
        registry.register(FakeModule("zeta"))
        registry.register(FakeModule("alpha"))
        assert registry.start_order() == ("alpha", "zeta")

    def test_cycle_detected(self) -> None:
        registry = ModuleRegistry()
        registry.register(FakeModule("a", ("b",)))
        registry.register(FakeModule("b", ("a",)))
        with pytest.raises(KernelError) as excinfo:
            registry.start_order()
        assert excinfo.value.code == "KRN-012"

    def test_unknown_dependency_rejected(self) -> None:
        registry = ModuleRegistry()
        registry.register(FakeModule("a", ("ghost",)))
        with pytest.raises(KernelError) as excinfo:
            registry.start_order()
        assert excinfo.value.code == "KRN-013"

    def test_duplicate_name_rejected(self) -> None:
        registry = ModuleRegistry()
        registry.register(FakeModule("a"))
        with pytest.raises(KernelError) as excinfo:
            registry.register(FakeModule("a"))
        assert excinfo.value.code == "KRN-010"


class TestHealthMonitor:
    def test_worst_state_wins(self) -> None:
        monitor = HealthMonitor(clock=ManualClock(T0))
        monitor.report("a", HealthState.HEALTHY)
        monitor.report("b", HealthState.WARNING)
        assert monitor.overall() is HealthState.WARNING
        monitor.report("c", HealthState.CRITICAL)
        assert monitor.overall() is HealthState.CRITICAL

    def test_empty_monitor_is_offline(self) -> None:
        assert HealthMonitor(clock=ManualClock(T0)).overall() is HealthState.OFFLINE

    def test_reports_are_timestamped_and_sorted(self) -> None:
        clock = ManualClock(T0)
        monitor = HealthMonitor(clock=clock)
        monitor.report("zeta", HealthState.HEALTHY)
        clock.advance_ms(1000)
        monitor.report("alpha", HealthState.HEALTHY, detail=1)
        snapshot = monitor.snapshot()
        assert [r.component for r in snapshot] == ["alpha", "zeta"]
        assert monitor.component("alpha").checked_at == T0.add_ms(1000)
