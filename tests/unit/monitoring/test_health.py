"""Health engine: dependency propagation and heartbeat freshness."""

from apex.core.enums import HealthState
from apex.core.time.clock import ManualClock
from apex.kernel.health import HealthMonitor
from apex.kernel.modules import ModuleRegistry
from apex.monitoring.health import HealthEngine
from apex.monitoring.records import HeartbeatRecord

from tests.conftest import T0


class _Module:
    """A registry module with a fixed health verdict."""

    def __init__(
        self,
        name: str,
        health: HealthState,
        dependencies: tuple[str, ...] = (),
    ) -> None:
        self._name = name
        self._health = health
        self._dependencies = dependencies

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self._dependencies

    async def start(self) -> None:  # pragma: no cover - registry contract
        return

    async def stop(self) -> None:  # pragma: no cover - registry contract
        return

    def health(self) -> HealthState:
        return self._health


def engine(*modules: _Module) -> HealthEngine:
    registry = ModuleRegistry()
    for module in modules:
        registry.register(module)
    return HealthEngine(
        registry=registry, monitor=HealthMonitor(clock=ManualClock(T0))
    )


class TestDependencyPropagation:
    def test_all_healthy_stays_healthy(self) -> None:
        reports = engine(
            _Module("base", HealthState.HEALTHY),
            _Module("upper", HealthState.HEALTHY, dependencies=("base",)),
        ).assess()
        assert all(report.state is HealthState.HEALTHY for report in reports)

    def test_offline_dependency_degrades_dependent_to_critical(self) -> None:
        health_engine = engine(
            _Module("base", HealthState.OFFLINE),
            _Module("upper", HealthState.HEALTHY, dependencies=("base",)),
        )
        by_name = {report.component: report for report in health_engine.assess()}
        assert by_name["base"].state is HealthState.OFFLINE
        assert by_name["upper"].state is HealthState.CRITICAL
        assert by_name["upper"].detail == "degraded via dependency"

    def test_warning_propagates_one_level_down(self) -> None:
        health_engine = engine(
            _Module("base", HealthState.WARNING),
            _Module("mid", HealthState.HEALTHY, dependencies=("base",)),
            _Module("top", HealthState.HEALTHY, dependencies=("mid",)),
        )
        by_name = {report.component: report for report in health_engine.assess()}
        assert by_name["mid"].state is HealthState.WARNING
        assert by_name["top"].state is HealthState.WARNING

    def test_overall_is_worst_component(self) -> None:
        health_engine = engine(
            _Module("base", HealthState.HEALTHY),
            _Module("upper", HealthState.CRITICAL, dependencies=("base",)),
        )
        reports = health_engine.assess()
        assert health_engine.overall(reports) is HealthState.CRITICAL


class TestHeartbeatAges:
    def test_staleness_threshold(self) -> None:
        beats = [
            HeartbeatRecord(component="fresh", beat_at=T0),
            HeartbeatRecord(
                component="stale", beat_at=T0.add_ms(-20_000)
            ),
        ]
        ages = HealthEngine.heartbeat_ages(
            beats, now=T0.add_ms(1_000), stale_ms=10_000
        )
        by_name = {age.component: age for age in ages}
        assert not by_name["fresh"].stale
        assert by_name["fresh"].age_ms == 1_000
        assert by_name["stale"].stale
        assert by_name["stale"].age_ms == 21_000
