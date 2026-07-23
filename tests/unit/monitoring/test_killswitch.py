"""Kill switch: transitions, permissions, auto-engage, SAFE_MODE cancel."""

import asyncio
from pathlib import Path

import pytest
from apex.core.exceptions import MonitoringError
from apex.core.time.clock import ManualClock
from apex.monitoring.collector import TelemetryCollector
from apex.monitoring.killswitch import KillSwitchEngine
from apex.monitoring.records import AlertSeverity, KillSwitchLevel
from apex.monitoring.slo import ErrorBudgetTracker

from tests.conftest import T0
from tests.unit.monitoring.support import logger, make_bus, settings, store_at


async def engine(
    tmp_path: Path,
    clock: ManualClock,
    *,
    canceller: object = None,
    auto: bool = True,
) -> KillSwitchEngine:
    store = store_at(tmp_path)
    await store.open()
    return KillSwitchEngine(
        settings=settings(kill_switch_auto_engage=auto),
        store=store,
        bus=make_bus(clock),
        clock=clock,
        logger=logger(),
        order_canceller=canceller,  # type: ignore[arg-type]
    )


class TestTransitions:
    def test_default_level_allows_everything(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            assert (await switch.level()) is KillSwitchLevel.NONE
            assert await switch.allows_new_entries()
            assert await switch.allows_processing()

        asyncio.run(scenario())

    def test_engage_and_release_ladder(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            await switch.engage(
                KillSwitchLevel.ENTRIES_DISABLED, reason="test", actor="op"
            )
            assert not await switch.allows_new_entries()
            assert await switch.allows_processing()
            await switch.engage(KillSwitchLevel.PAUSED, reason="test", actor="op")
            assert not await switch.allows_processing()
            record = await switch.release(reason="done", actor="op")
            assert record.level is KillSwitchLevel.NONE
            assert await switch.allows_new_entries()

        asyncio.run(scenario())

    def test_engage_none_is_rejected(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            with pytest.raises(MonitoringError):
                await switch.engage(KillSwitchLevel.NONE, reason="x", actor="op")

        asyncio.run(scenario())


class TestAutoEngage:
    def test_below_threshold_does_nothing(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            engaged = await switch.auto_engage(
                severity=AlertSeverity.HIGH, reason="x"
            )
            assert engaged is False
            assert (await switch.level()) is KillSwitchLevel.NONE

        asyncio.run(scenario())

    def test_disabled_policy_never_engages(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0), auto=False)
            engaged = await switch.auto_engage(
                severity=AlertSeverity.EMERGENCY, reason="x"
            )
            assert engaged is False

        asyncio.run(scenario())

    def test_no_downgrade_when_already_stricter(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            await switch.engage(KillSwitchLevel.SAFE_MODE, reason="x", actor="op")
            engaged = await switch.auto_engage(
                severity=AlertSeverity.EMERGENCY, reason="y"
            )
            assert engaged is False
            assert (await switch.level()) is KillSwitchLevel.SAFE_MODE

        asyncio.run(scenario())


class TestSafeMode:
    def test_safe_mode_cancels_resting_orders(self, tmp_path: Path) -> None:
        calls = {"count": 0}

        async def canceller() -> int:
            calls["count"] += 1
            return 2

        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0), canceller=canceller)
            await switch.engage(KillSwitchLevel.SAFE_MODE, reason="x", actor="op")
            assert calls["count"] == 1
            assert await switch.cancel_resting_orders() == 2
            assert calls["count"] == 2

        asyncio.run(scenario())

    def test_without_canceller_returns_zero(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            switch = await engine(tmp_path, ManualClock(T0))
            assert await switch.cancel_resting_orders() == 0

        asyncio.run(scenario())


class TestErrorBudget:
    def test_budget_exhaustion_blocks_promotion(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            store = store_at(tmp_path)
            await store.open()
            config = settings()
            tracker = ErrorBudgetTracker(settings=config, store=store, clock=clock)
            collector = TelemetryCollector(store=store, clock=clock, logger=logger())
            for _ in range(5):
                collector.operation()
            await collector.flush()
            healthy = await tracker.status()
            assert not healthy.exhausted
            assert await tracker.promotion_permitted()
            for _ in range(2):  # 2 errors / 5 operations = 40% > 20% budget
                collector.error()
            await collector.flush()
            exhausted = await tracker.status()
            assert exhausted.exhausted
            assert exhausted.errors == 2
            assert not await tracker.promotion_permitted()
            await store.close()

        asyncio.run(scenario())

    def test_thin_sample_never_exhausts(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            store = store_at(tmp_path)
            await store.open()
            tracker = ErrorBudgetTracker(
                settings=settings(), store=store, clock=clock
            )
            collector = TelemetryCollector(store=store, clock=clock, logger=logger())
            collector.operation()
            collector.error()
            await collector.flush()
            status = await tracker.status()
            assert status.error_rate == 1.0
            assert not status.exhausted  # below slo_min_operations
            await store.close()

        asyncio.run(scenario())
