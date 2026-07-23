"""Promotion pipeline: shadow evaluation, lifecycle, guard, queue pause."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from apex.contracts.engines import DecisionSnapshot
from apex.core.config import AppConfig
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.decision.kernel import DecisionParams
from apex.kernel.kernel import Kernel
from apex.optimization.objective import ObjectiveWeights
from apex.portfolio.config import portfolio_settings
from apex.portfolio.store import PositionRecord, SqlitePortfolioRepository
from apex.research.promotion import evaluate_shadow
from apex.research.service import ResearchService
from apex.research.store import (
    PROMOTION_PASSED,
    PROMOTION_PROMOTED,
    PROMOTION_REJECTED,
    PROMOTION_ROLLED_BACK,
    PROMOTION_SHADOW,
    SqliteResearchRepository,
)

from tests.conftest import T0
from tests.unit.decision.test_decision import bullish_vector, make_bar, strong_channels

H1_MS = Timeframe.H1.duration_ms


def snapshots(count: int) -> list[DecisionSnapshot]:
    """Rising confirmed bars wrapped as decision snapshots."""
    result = []
    for index in range(count):
        base = 100.0 + index
        bar = make_bar(index, base, base + 2.2, base - 0.4, base + 2.0)
        result.append(
            DecisionSnapshot(
                bar=bar,
                vector=bullish_vector(),
                probability_long=0.85,
                probability_short=0.05,
                channels=strong_channels(),
                macro_high=float(bar.close.value) + 50.0,
                macro_low=float(bar.close.value) - 50.0,
            )
        )
    return result


def shadow_params() -> DecisionParams:
    return DecisionParams(
        atr_length=3,
        ema_length=3,
        rvol_gate_enabled=False,
        similarity_cooldown_enabled=False,
        cooldown_bars=1,
        flatness_gate_enabled=False,
    )


class TestEvaluateShadow:
    def test_insufficient_forward_bars_fails_with_reason(self) -> None:
        report = evaluate_shadow(
            snapshots=snapshots(3),
            base_params=shadow_params(),
            candidate_overrides={},
            baseline_overrides=None,
            context=MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0),
            clock=ManualClock(T0),
            weights=ObjectiveWeights(),
            horizon_bars=6,
            min_bars=10,
            tolerance=0.0,
        )
        assert not report.passed
        assert "insufficient forward bars" in report.reason

    def test_identical_candidate_passes_within_tolerance(self) -> None:
        report = evaluate_shadow(
            snapshots=snapshots(30),
            base_params=shadow_params(),
            candidate_overrides={},
            baseline_overrides=None,
            context=MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0),
            clock=ManualClock(T0),
            weights=ObjectiveWeights(),
            horizon_bars=6,
            min_bars=10,
            tolerance=0.0,
        )
        assert report.passed
        assert report.candidate_score == report.baseline_score
        assert report.bars == 30
        payload = json.loads(report.to_json())
        assert payload["passed"] is True
        assert payload["candidate"]["signals"] == report.candidate_signals


class TestPromotionStore:
    def test_lifecycle_states_and_latest(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = SqliteResearchRepository(
                database_path=tmp_path / "research.sqlite"
            )
            await store.open()
            promotion_id = await store.register_promotion(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                kind="signal",
                artifact_path="/tmp/a.json",
                baseline_artifact=None,
                registered_at=T0,
            )
            shadows = await store.promotions(status=PROMOTION_SHADOW)
            assert len(shadows) == 1
            await store.mark_promotion_evaluated(
                promotion_id,
                status=PROMOTION_PASSED,
                report='{"passed": true}',
                at=T0.add_ms(1_000),
            )
            record = await store.promotion(promotion_id)
            assert record is not None
            assert record.status == PROMOTION_PASSED
            assert record.report == '{"passed": true}'
            await store.mark_promotion_decided(
                promotion_id,
                status=PROMOTION_PROMOTED,
                actor="operator",
                at=T0.add_ms(2_000),
            )
            latest = await store.latest_promotion(
                "BTCUSDT", Timeframe.H1, "signal", status=PROMOTION_PROMOTED
            )
            assert latest is not None
            assert latest.decided_by == "operator"
            assert latest.decided_at is not None
            await store.close()

        asyncio.run(scenario())

    def test_flags_roundtrip(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = SqliteResearchRepository(
                database_path=tmp_path / "research.sqlite"
            )
            await store.open()
            assert await store.get_flag("queue_paused") is None
            await store.set_flag("queue_paused", "1")
            assert await store.get_flag("queue_paused") == "1"
            await store.set_flag("queue_paused", "0")
            assert await store.get_flag("queue_paused") == "0"
            await store.close()

        asyncio.run(scenario())


class TestPromotionService:
    """Lifecycle behavior through the booted platform services."""

    def test_promote_reject_and_queue_pause(self, config_dir: Path) -> None:
        async def scenario() -> None:
            kernel = Kernel(config_dir=config_dir, clock=ManualClock(T0))
            await kernel.boot()
            try:
                research = kernel.container.resolve(ResearchService)
                store = kernel.container.resolve(SqliteResearchRepository)
                missing = await research.promote(999, actor="op")
                assert not missing.ok
                assert missing.error is not None
                assert missing.error.code == "RES-007"
                promotion_id = await store.register_promotion(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    kind="signal",
                    artifact_path=str(config_dir / "artifact.json"),
                    baseline_artifact=None,
                    registered_at=T0,
                )
                premature = await research.promote(promotion_id, actor="op")
                assert not premature.ok
                assert premature.error is not None
                assert premature.error.code == "RES-008"
                rejected = await research.reject_promotion(promotion_id, actor="op")
                assert rejected.ok
                record = await store.promotion(promotion_id)
                assert record is not None
                assert record.status == PROMOTION_REJECTED
                re_reject = await research.reject_promotion(promotion_id, actor="op")
                assert not re_reject.ok
                assert re_reject.error is not None
                assert re_reject.error.code == "RES-009"
                assert not await research.queue_paused()
                await research.pause_queue()
                assert await research.queue_paused()
                drained = await research.orchestrate(
                    limit=1, default_window_bars=100
                )
                assert drained.unwrap().drained == 0  # paused queue never drains
                await research.resume_queue()
                assert not await research.queue_paused()
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_passed_promotion_activates_on_approval(self, config_dir: Path) -> None:
        async def scenario() -> None:
            kernel = Kernel(config_dir=config_dir, clock=ManualClock(T0))
            await kernel.boot()
            try:
                research = kernel.container.resolve(ResearchService)
                store = kernel.container.resolve(SqliteResearchRepository)
                artifact = config_dir / "candidate.json"
                artifact.write_text(
                    json.dumps({"optimized_parameters": {"cooldown_bars": 2.0}}),
                    encoding="utf-8",
                )
                promotion_id = await store.register_promotion(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    kind="signal",
                    artifact_path=str(artifact),
                    baseline_artifact=None,
                    registered_at=T0,
                )
                await store.mark_promotion_evaluated(
                    promotion_id,
                    status=PROMOTION_PASSED,
                    report="{}",
                    at=T0.add_ms(1_000),
                )
                approved = await research.promote(promotion_id, actor="operator")
                assert approved.ok
                overrides = await research.active_overrides("BTCUSDT", Timeframe.H1)
                assert overrides == {"cooldown_bars": 2.0}
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_promotion_guard_rolls_back_degrading_artifact(
        self, config_dir: Path
    ) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            kernel = Kernel(config_dir=config_dir, clock=clock)
            await kernel.boot()
            try:
                research = kernel.container.resolve(ResearchService)
                store = kernel.container.resolve(SqliteResearchRepository)
                portfolio = kernel.container.resolve(SqlitePortfolioRepository)
                config = kernel.container.resolve(AppConfig)
                portfolio_id = portfolio_settings(
                    config.section("portfolio")
                ).portfolio_id
                baseline = config_dir / "baseline.json"
                candidate = config_dir / "candidate.json"
                for path in (baseline, candidate):
                    path.write_text(
                        json.dumps({"optimized_parameters": {}}), encoding="utf-8"
                    )
                await store.activate_version(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    kind="signal",
                    artifact_path=str(baseline),
                    activated_at=T0,
                )
                await store.activate_version(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    kind="signal",
                    artifact_path=str(candidate),
                    activated_at=T0.add_ms(1_000),
                )
                promotion_id = await store.register_promotion(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.H1,
                    kind="signal",
                    artifact_path=str(candidate),
                    baseline_artifact=str(baseline),
                    registered_at=T0,
                )
                await store.mark_promotion_decided(
                    promotion_id,
                    status=PROMOTION_PROMOTED,
                    actor="operator",
                    at=T0.add_ms(2_000),
                )
                await portfolio.upsert_positions(
                    [
                        _losing_position(portfolio_id, index)
                        for index in range(3)
                    ]
                )
                untouched = await research.apply_promotion_guard(
                    "BTCUSDT", Timeframe.H1, min_trades=5, floor_r=-2.0
                )
                assert untouched is None  # not enough trades yet
                restored = await research.apply_promotion_guard(
                    "BTCUSDT", Timeframe.H1, min_trades=3, floor_r=-2.0
                )
                assert restored == str(baseline)
                record = await store.promotion(promotion_id)
                assert record is not None
                assert record.status == PROMOTION_ROLLED_BACK
                assert record.decided_by == "promotion_guard"
                # The guard never fires twice for the same promotion.
                again = await research.apply_promotion_guard(
                    "BTCUSDT", Timeframe.H1, min_trades=3, floor_r=-2.0
                )
                assert again is None
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())


def _losing_position(portfolio_id: str, index: int) -> PositionRecord:
    """One closed losing trade after the promotion decision."""
    opened = Timestamp(epoch_ms=T0.epoch_ms + 3_000 + index * H1_MS)
    return PositionRecord(
        portfolio_id=portfolio_id,
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        entry_bar_time=opened,
        position_id=f"guard-{index}",
        lineage_id=f"guard-{index}",
        direction="long",
        quantity=Decimal("1"),
        entry=Decimal("100"),
        stop=Decimal("99"),
        target=Decimal("103"),
        risk_amount=Decimal("1"),
        opened_at=opened,
        status="closed",
        closed_at=opened.add_ms(H1_MS),
        exit_price=Decimal("99"),
        realized_pnl=Decimal("-1"),
        realized_r=-1.0,
        close_reason="stop",
    )
