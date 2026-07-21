"""Feature platform: registry, store, structure engine, pipeline."""

import asyncio
import io
from decimal import Decimal
from pathlib import Path

import pytest
from apex.core.context import MarketContext
from apex.core.enums import ClockSourceType, Timeframe
from apex.core.events.bus import InProcessEventBus
from apex.core.events.journal import EventJournal
from apex.core.exceptions import FeatureError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import ManualClock
from apex.core.types import Confidence, Price, QualityScore, Reliability, Volume, Weight
from apex.core.versioning import SemanticVersion
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.events import FeatureEvent
from apex.features.pipeline import FeatureComputationPipeline
from apex.features.registry import FeatureDefinition, FeatureRegistry
from apex.features.structure.definitions import structure_definitions
from apex.features.structure.engine import (
    FEATURE_NAMES,
    MarketStructureEngine,
    StructureParams,
)
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Small, fast parameters for deterministic scenario construction.
PARAMS = StructureParams(
    pivot_lookback=2,
    atr_length=3,
    displacement_body_atr=1.2,
    equal_tolerance_atr=0.10,
    break_decay=0.985,
)


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.features")


def bar_from_ohlc(index: int, o: float, h: float, low: float, c: float) -> Bar:
    return Bar(
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        open_time=T0.add_ms(index * H1_MS),
        open=Price(Decimal(str(o))),
        high=Price(Decimal(str(h))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(c))),
        volume=Volume(Decimal(100)),
        is_closed=True,
        quality=QualityScore(1.0),
    )


def series_from_closes(closes: list[float], *, spread: float = 1.0) -> list[Bar]:
    """Deterministic bars: open at the midpoint of the move, extremes
    bracketing the body by ``spread`` (keeps adjacent highs distinct so
    strict pivot semantics are exercised faithfully)."""
    bars: list[Bar] = []
    previous = float(closes[0])
    for index, raw in enumerate(closes):
        close = float(raw)
        o = (previous + close) / 2.0
        h = max(o, close) + spread
        low = min(o, close) - spread
        bars.append(bar_from_ohlc(index, o, h, low, close))
        previous = close
    return bars


def value_of(features: list[Feature], name: str, index: int) -> float:
    """Raw value of a named feature at a given bar index."""
    anchor = T0.add_ms(index * H1_MS)
    for feature in features:
        if feature.name == name and feature.bar_open_time == anchor:
            return float(feature.value)
    raise AssertionError(f"{name} not found at bar {index}")


def compute(bars: list[Bar]) -> list[Feature]:
    engine = MarketStructureEngine(params=PARAMS, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    return list(engine.compute(bars, context).unwrap())


class TestRegistry:
    def make_definition(self, name: str = "structure.trend_direction") -> FeatureDefinition:
        return FeatureDefinition(
            name=name,
            family="structure",
            description="test",
            version=SemanticVersion(1, 0, 0),
        )

    def test_register_and_lookup(self) -> None:
        registry = FeatureRegistry()
        registry.register(self.make_definition())
        assert registry.is_registered("structure.trend_direction")
        assert registry.get("structure.trend_direction").family == "structure"
        assert registry.families == ("structure",)

    def test_duplicate_rejected(self) -> None:
        registry = FeatureRegistry()
        registry.register(self.make_definition())
        with pytest.raises(FeatureError) as excinfo:
            registry.register(self.make_definition())
        assert excinfo.value.code == "FEA-002"

    def test_name_must_be_family_namespaced(self) -> None:
        with pytest.raises(FeatureError) as excinfo:
            FeatureDefinition(
                name="trend_direction",
                family="structure",
                description="x",
                version=SemanticVersion(1, 0, 0),
            )
        assert excinfo.value.code == "FEA-001"

    def test_unknown_lookup_rejected(self) -> None:
        with pytest.raises(FeatureError) as excinfo:
            FeatureRegistry().get("structure.nope")
        assert excinfo.value.code == "FEA-003"

    def test_structure_definitions_cover_engine_names(self) -> None:
        registry = FeatureRegistry()
        registry.register_all(structure_definitions(PARAMS))
        for name in FEATURE_NAMES:
            assert registry.is_registered(name)


class TestStructureEngine:
    def test_bos_up_on_break_of_swing_high(self) -> None:
        # Swing high 110 at index 2 (confirmed at 4); break at index 7.
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 115, 114, 113]
        bars = series_from_closes(closes)
        features = compute(bars)
        assert value_of(features, "structure.bos_up", 7) == 1.0
        assert value_of(features, "structure.choch_up", 7) == 0.0
        assert value_of(features, "structure.trend_direction", 7) == 1.0
        # Break quality decays afterwards but stays positive.
        q7 = value_of(features, "structure.break_quality", 7)
        q9 = value_of(features, "structure.break_quality", 9)
        assert q7 > q9 > 0.0

    def test_choch_down_after_uptrend(self) -> None:
        # Uptrend established via BOS up, then break below the swing low.
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 115, 114, 113, 112, 96, 95, 94]
        bars = series_from_closes(closes)
        features = compute(bars)
        # Swing low 101 (close 102 - spread 1) at index 4, confirmed at 6.
        choch_bars = [
            i
            for i in range(PARAMS.warmup_bars, len(bars))
            if value_of(features, "structure.choch_down", i) == 1.0
        ]
        assert choch_bars, "expected a CHoCH down after the uptrend broke"
        first = choch_bars[0]
        assert value_of(features, "structure.trend_direction", first) == -1.0
        assert value_of(features, "structure.bos_down", first) == 0.0

    def test_first_break_without_trend_is_bos(self) -> None:
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 115]
        features = compute(series_from_closes(closes))
        assert value_of(features, "structure.bos_up", 7) == 1.0
        assert value_of(features, "structure.choch_up", 7) == 0.0

    def test_no_features_during_warmup(self) -> None:
        closes: list[float] = [100, 101, 102, 103, 104, 105, 106, 107]
        features = compute(series_from_closes(closes))
        earliest = min(f.bar_open_time.epoch_ms for f in features)
        assert earliest >= T0.add_ms(PARAMS.warmup_bars * H1_MS).epoch_ms

    def test_forming_bar_rejected(self) -> None:
        bars = series_from_closes([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        from dataclasses import replace

        bars[-1] = replace(bars[-1], is_closed=False)
        engine = MarketStructureEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "DAT-004"

    def test_unordered_bars_rejected(self) -> None:
        bars = series_from_closes([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        bars = [bars[1], bars[0], *bars[2:]]
        engine = MarketStructureEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "FEA-010"

    def test_dealing_range_and_normalization(self) -> None:
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 115, 114, 113]
        features = compute(series_from_closes(closes))
        dr = value_of(features, "structure.dealing_range_position", 9)
        assert 0.0 <= dr <= 1.0
        for feature in features:
            assert -1.0 <= feature.normalized_value <= 1.0

    def test_sweep_high_detection(self) -> None:
        # Swing high 110+1=111 at index 2; index 7 wicks above and closes below.
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 105, 104, 103]
        bars = series_from_closes(closes)
        from dataclasses import replace

        bars[7] = replace(bars[7], high=Price(Decimal("120")))
        features = compute(bars)
        assert value_of(features, "structure.sweep_high", 7) == 1.0
        assert value_of(features, "structure.bos_up", 7) == 0.0


class TestPipeline:
    def make_pipeline(self, tmp_path: Path) -> tuple[
        FeatureComputationPipeline,
        SqliteBarRepository,
        SqliteFeatureRepository,
        InProcessEventBus,
    ]:
        bars = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        store = SqliteFeatureRepository(database_path=tmp_path / "features.sqlite")
        clock = ManualClock(T0.add_ms(100 * H1_MS), source=ClockSourceType.SIMULATION)
        bus = InProcessEventBus(
            journal=EventJournal(capacity=1000),
            clock=clock,
            logger=make_logger(),
            fail_fast=True,
        )
        registry = FeatureRegistry()
        registry.register_all(structure_definitions(PARAMS))
        pipeline = FeatureComputationPipeline(
            exchange_id="toobit",
            engines=(MarketStructureEngine(params=PARAMS, clock=clock),),
            registry=registry,
            bar_repository=bars,
            feature_repository=store,
            bus=bus,
            clock=clock,
            logger=make_logger(),
        )
        return pipeline, bars, store, bus

    def test_end_to_end_compute_and_store(self, tmp_path: Path) -> None:
        closes: list[float] = [100, 105, 110, 104, 102, 103, 104, 115, 114, 113]

        async def scenario() -> None:
            pipeline, bars, store, bus = self.make_pipeline(tmp_path)
            await bars.open()
            await store.open()
            await bars.upsert(series_from_closes(closes))
            result = await pipeline.compute(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(20 * H1_MS)
            )
            summary = result.unwrap()
            assert summary.bars_loaded == 10
            assert summary.families == ("structure",)
            emitted_bars = 10 - PARAMS.warmup_bars
            assert summary.features_stored == emitted_bars * len(FEATURE_NAMES)
            # Vector query returns the full set for one bar.
            vector = await store.get_vector(
                "toobit", "BTCUSDT", Timeframe.H1, T0.add_ms(7 * H1_MS)
            )
            assert len(vector) == len(FEATURE_NAMES)
            names = {f.name for f in vector}
            assert "structure.bos_up" in names
            # Series query round-trips values.
            series = await store.get_series(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                "structure.trend_direction",
                start=T0,
                end=T0.add_ms(20 * H1_MS),
            )
            assert series[-1].value == 1.0
            event_types = [e.event_type for e in bus.journal.replay()]
            assert FeatureEvent.FEATURES_COMPUTED.value in event_types
            # Recomputation is idempotent.
            second = await pipeline.compute(
                "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(20 * H1_MS)
            )
            assert second.unwrap().features_stored == summary.features_stored
            assert await store.count("toobit", "BTCUSDT", Timeframe.H1) == (
                summary.features_stored
            )
            await store.close()
            await bars.close()

        asyncio.run(scenario())

    def test_unregistered_feature_rejected(self, tmp_path: Path) -> None:
        class RogueEngine:
            @property
            def family(self) -> str:
                return "structure"

            @property
            def feature_names(self) -> tuple[str, ...]:
                return ("structure.rogue",)

            def compute(self, bars: object, context: object) -> Result[tuple[Feature, ...]]:
                rogue = Feature(
                    created_at=T0,
                    name="structure.rogue",
                    family="structure",
                    exchange="toobit",
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    bar_open_time=T0,
                    value=1.0,
                    normalized_value=1.0,
                    weight=Weight(1.0),
                    confidence=Confidence(1.0),
                    reliability=Reliability(1.0),
                    source="tests",
                    computed_at=T0,
                )
                return Result.success((rogue,))

        async def scenario() -> None:
            _, bars, store, _ = self.make_pipeline(tmp_path)
            pipeline_rogue = FeatureComputationPipeline(
                exchange_id="toobit",
                engines=(RogueEngine(),),
                registry=FeatureRegistry(),
                bar_repository=bars,
                feature_repository=store,
                bus=InProcessEventBus(
                    journal=EventJournal(capacity=100),
                    clock=ManualClock(T0),
                    logger=make_logger(),
                    fail_fast=True,
                ),
                clock=ManualClock(T0),
                logger=make_logger(),
            )
            await bars.open()
            await store.open()
            with pytest.raises(FeatureError) as excinfo:
                await pipeline_rogue.compute(
                    "BTCUSDT", Timeframe.H1, start=T0, end=T0.add_ms(H1_MS)
                )
            assert excinfo.value.code == "FEA-004"
            await store.close()
            await bars.close()

        asyncio.run(scenario())
