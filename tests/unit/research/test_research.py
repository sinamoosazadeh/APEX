"""Research platform: learning fold parity, IC fold, kernel meta,
attribution, analyses, experiments, orchestration store."""

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.exceptions import ValidationError
from apex.core.time.clock import ManualClock
from apex.decision.store import DecisionRecord
from apex.domain.learning import (
    CHANNEL_COUNT,
    LearningParams,
    LearningState,
    SetupStats,
)
from apex.portfolio.store import PositionRecord
from apex.research.analysis import (
    detect_drift,
    measure_calibration,
    measure_execution_quality,
)
from apex.research.attribution import join_outcomes
from apex.research.experiments import bootstrap_comparison
from apex.research.store import JOB_COMPLETED, JOB_PENDING, SqliteResearchRepository

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms
PARAMS = LearningParams()


class TestLearningState:
    def test_fresh_matches_the_aice_priors(self) -> None:
        state = LearningState.fresh(PARAMS)
        assert state.alpha == (6.0,) * CHANNEL_COUNT
        assert state.beta == (6.0,) * CHANNEL_COUNT
        assert state.channel_factor(0, PARAMS) == pytest.approx(1.0)
        assert state.setup_factor("Anything") == pytest.approx(1.0)
        assert state.calibrate(0.7, PARAMS) == pytest.approx(0.7)

    def test_fold_updates_follow_f_update_feature(self) -> None:
        state = LearningState.fresh(PARAMS)
        scores = (0.8,) + (0.1,) * (CHANNEL_COUNT - 1)  # only channel 0 counts
        folded = state.fold_outcome(
            setup="Turtle Soup Long", win=True, realized_r=2.0,
            probability=0.72, channel_scores=scores,
        )
        assert folded.alpha[0] == pytest.approx(6.8)  # win adds the score
        assert folded.beta[0] == pytest.approx(6.0)
        assert folded.alpha[1] == pytest.approx(6.0)  # below 0.20 skipped
        assert folded.r_sum[0] == pytest.approx(1.6)  # r x score
        assert folded.trades[0] == pytest.approx(0.8)
        assert folded.calibration_trades[7] == 1.0  # bin(0.72) = 7
        assert folded.calibration_wins[7] == 1.0
        assert dict(folded.setups)["Turtle Soup Long"].trades == 1.0

    def test_channel_factor_golden(self) -> None:
        # Hand-computed f_feature_factor: a=16, b=6, tr=25, rs=25.
        state = LearningState.fresh(PARAMS)
        state = LearningState(
            alpha=(16.0,) + (6.0,) * (CHANNEL_COUNT - 1),
            beta=(6.0,) * CHANNEL_COUNT,
            r_sum=(25.0,) + (0.0,) * (CHANNEL_COUNT - 1),
            trades=(25.0,) + (0.0,) * (CHANNEL_COUNT - 1),
            calibration_wins=(0.0,) * 10,
            calibration_trades=(0.0,) * 10,
        )
        # post = 16/22, perfEdge = 0.4545..., expR = 1 -> rEdge 1;
        # sample = 1 -> 1 + 0.65 x (0.31818 + 0.3) = 1.4018...
        assert state.channel_factor(0, PARAMS) == pytest.approx(1.40181, abs=1e-4)

    def test_setup_factor_golden(self) -> None:
        state = LearningState(
            alpha=(6.0,) * CHANNEL_COUNT, beta=(6.0,) * CHANNEL_COUNT,
            r_sum=(0.0,) * CHANNEL_COUNT, trades=(0.0,) * CHANNEL_COUNT,
            calibration_wins=(0.0,) * 10, calibration_trades=(0.0,) * 10,
            setups=(("Breaker Long", SetupStats(trades=30.0, wins=24.0, r_sum=30.0)),),
        )
        # wr = 25/32 = 0.78125, expR = 1, sample = 1
        # factor = 1 + (0.28125 x 0.5 + 0.2) = 1.3406 -> ceil 1.25
        assert state.setup_factor("Breaker Long") == pytest.approx(1.25)

    def test_calibrator_blends_toward_observed(self) -> None:
        state = LearningState(
            alpha=(6.0,) * CHANNEL_COUNT, beta=(6.0,) * CHANNEL_COUNT,
            r_sum=(0.0,) * CHANNEL_COUNT, trades=(0.0,) * CHANNEL_COUNT,
            calibration_wins=(0.0,) * 8 + (5.0, 0.0),
            calibration_trades=(0.0,) * 8 + (100.0, 0.0),
        )
        # bin 8: wr = 6/102 = 0.0588; blend = min(100/25, 0.65) = 0.65
        # 0.85 x 0.35 + 0.0588 x 0.65 = 0.3357
        assert state.calibrate(0.85, PARAMS) == pytest.approx(0.33574, abs=1e-4)

    def test_json_round_trip(self) -> None:
        state = LearningState.fresh(PARAMS).fold_outcome(
            setup="X", win=False, realized_r=-1.0, probability=0.6,
            channel_scores=(0.5,) * CHANNEL_COUNT,
        )
        parsed = LearningState.from_json(state.to_json())
        assert parsed == state

    def test_wrong_score_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearningState.fresh(PARAMS).fold_outcome(
                setup="X", win=True, realized_r=1.0, probability=0.5,
                channel_scores=(0.5,),
            )


def closed_position(index: int, *, win: bool, symbol: str = "BTCUSDT") -> PositionRecord:
    return PositionRecord(
        portfolio_id="default", exchange="toobit", symbol=symbol,
        timeframe=Timeframe.H1, entry_bar_time=T0.add_ms(index * H1_MS),
        position_id=f"p{index}", lineage_id=f"l{index}", direction="long",
        quantity=Decimal(1), entry=Decimal(100), stop=Decimal(98),
        target=Decimal(106), risk_amount=Decimal(2),
        opened_at=T0.add_ms(index * H1_MS), status="closed",
        closed_at=T0.add_ms((index + 3) * H1_MS),
        exit_price=Decimal(106) if win else Decimal(98),
        realized_pnl=Decimal(6) if win else Decimal(-2),
        realized_r=3.0 if win else -1.0,
        close_reason="target" if win else "stop",
    )


def fired_decision(index: int, setup: str = "Breaker Long") -> DecisionRecord:
    return DecisionRecord(
        exchange="toobit", symbol="BTCUSDT", timeframe=Timeframe.H1,
        bar_open_time=T0.add_ms(index * H1_MS), action="signal",
        direction="long", setup=setup, probability=0.74, uncertainty=0.2,
        expected_r=1.1, contributors=8, failed_gates=(),
        entry=100.0, stop=98.0, targets=(102.0, 104.0, 106.0), computed_at=T0,
    )


class TestAttribution:
    def test_join_matches_and_counts(self) -> None:
        channels = {
            f"{name}_long": 0.6
            for name in (
                "structure", "liquidity", "orderblock", "fvg", "zone", "dna",
                "kinetic", "delta", "sequence", "trend", "mtf", "smt", "profile",
            )
        }
        result = join_outcomes(
            [closed_position(2, win=True), closed_position(9, win=False)],
            [fired_decision(2)],
            {T0.add_ms(2 * H1_MS).epoch_ms: channels},
        )
        assert result.closed_trades == 2
        assert len(result.outcomes) == 1  # bar 9 has no decision
        assert result.unmatched_decisions == 1
        outcome = result.outcomes[0]
        assert outcome.setup == "Breaker Long"
        assert outcome.win and outcome.realized_r == pytest.approx(3.0)
        assert outcome.channel_scores == (0.6,) * CHANNEL_COUNT


class TestAnalyses:
    def test_calibration_measurement(self) -> None:
        channels = (0.6,) * CHANNEL_COUNT
        from apex.research.attribution import TradeOutcome

        outcomes = [
            TradeOutcome(
                symbol="BTCUSDT", timeframe=Timeframe.H1, entry_bar_ms=0,
                closed_at_ms=1, setup="X", direction="long",
                probability=0.75, win=True, realized_r=2.0,
                channel_scores=channels,
            ),
            TradeOutcome(
                symbol="BTCUSDT", timeframe=Timeframe.H1, entry_bar_ms=2,
                closed_at_ms=3, setup="X", direction="long",
                probability=0.75, win=False, realized_r=-1.0,
                channel_scores=channels,
            ),
        ]
        report = measure_calibration(outcomes)
        assert report.trades == 2
        bin7 = report.bins[7]
        assert bin7.trades == 2
        assert bin7.predicted == pytest.approx(0.75)
        assert bin7.observed == pytest.approx(0.5)
        # Brier: ((0.25)^2 + (0.75)^2) / 2 = 0.3125
        assert report.brier_score == pytest.approx(0.3125)

    def test_drift_flags_a_shifted_series(self) -> None:
        steady = [0.45, 0.55] * 50
        shifted = [0.45, 0.55] * 40 + [0.9] * 20
        assert not detect_drift("steady", steady).drifting
        report = detect_drift("shifted", shifted)
        assert report.drifting and report.shift_z > 2.0

    def test_short_series_never_flags(self) -> None:
        assert not detect_drift("short", [1.0, 2.0, 3.0]).drifting

    def test_execution_quality_aggregation(self) -> None:
        from apex.execution.store import ExecutionRecord

        def record(status: str, slippage: str | None) -> ExecutionRecord:
            return ExecutionRecord(
                execution_id=f"e-{status}-{slippage}", portfolio_id="default",
                exchange="toobit", symbol="BTCUSDT", timeframe=Timeframe.H1,
                mode="paper", signal_bar_time=T0, direction="long",
                order_type="market", client_order_id="c", requested_at=T0,
                completed_at=T0, status=status, quantity=Decimal(1),
                decision_price=Decimal(100),
                fill_price=Decimal(101) if status == "filled" else None,
                fees=Decimal("0.06") if status == "filled" else Decimal(0),
                slippage=Decimal(slippage) if slippage else None,
                stop=Decimal(98), target=Decimal(106), reasons=(),
            )

        report = measure_execution_quality(
            [record("filled", "1.0"), record("filled", "3.0"), record("unfilled", None)]
        )
        assert report.filled == 2 and report.unfilled == 1
        assert report.fill_rate == pytest.approx(2 / 3)
        assert report.average_slippage == Decimal(2)


class TestBootstrap:
    def test_strong_candidate_gets_a_small_p(self) -> None:
        baseline = [-0.5, 0.2, -0.1, 0.3, -0.2, 0.1] * 5
        candidate = [1.5, 2.0, 1.8, 2.2, 1.6, 1.9] * 5
        result = bootstrap_comparison(baseline, candidate, resamples=400, seed=7)
        assert result.p_value < 0.05
        assert result.effect_size > 1.0

    def test_deterministic_and_neutral_on_empty(self) -> None:
        first = bootstrap_comparison([1.0, 2.0], [1.5, 2.5], resamples=200, seed=3)
        second = bootstrap_comparison([1.0, 2.0], [1.5, 2.5], resamples=200, seed=3)
        assert first == second
        assert bootstrap_comparison([], [1.0]).p_value == 1.0


class TestResearchStore:
    def test_job_and_version_lifecycle(self, tmp_path: Path) -> None:
        asyncio.run(self._lifecycle(tmp_path))

    async def _lifecycle(self, tmp_path: Path) -> None:
        store = SqliteResearchRepository(database_path=tmp_path / "research.sqlite")
        await store.open()
        try:
            await store.enqueue_job(
                symbol="ETHUSDT", timeframe=Timeframe.H1, kind="signal",
                priority=1, seed=7, window_bars=0, created_at=T0,
            )
            await store.enqueue_job(
                symbol="BTCUSDT", timeframe=Timeframe.H1, kind="signal",
                priority=0, seed=7, window_bars=0, created_at=T0.add_ms(1),
            )
            job = await store.next_pending_job()
            assert job is not None and job.symbol == "BTCUSDT"  # priority first
            await store.mark_job(
                job.job_id, status=JOB_COMPLETED,
                completed_at=T0.add_ms(2), result="done", bump_attempts=True,
            )
            remaining = await store.jobs(status=JOB_PENDING)
            assert len(remaining) == 1 and remaining[0].symbol == "ETHUSDT"

            first = await store.activate_version(
                symbol="BTCUSDT", timeframe=Timeframe.H1, kind="signal",
                artifact_path="/a/v1.json", activated_at=T0,
            )
            second = await store.activate_version(
                symbol="BTCUSDT", timeframe=Timeframe.H1, kind="signal",
                artifact_path="/a/v2.json", activated_at=T0.add_ms(1),
            )
            assert (first, second) == (1, 2)
            active = await store.active_artifact("BTCUSDT", Timeframe.H1, "signal")
            assert active == "/a/v2.json"
            rolled = await store.rollback_version("BTCUSDT", Timeframe.H1, "signal")
            assert rolled == "/a/v1.json"
            assert (
                await store.active_artifact("BTCUSDT", Timeframe.H1, "signal")
                == "/a/v1.json"
            )

            version = await store.save_learning_artifact(
                symbol="BTCUSDT", timeframe=Timeframe.H1,
                payload=LearningState.fresh(PARAMS).to_json(),
                outcomes=0, created_at=T0,
            )
            assert version == 1
            payload = await store.latest_learning_artifact("BTCUSDT", Timeframe.H1)
            assert payload is not None
            assert LearningState.from_json(payload) == LearningState.fresh(PARAMS)
        finally:
            await store.close()


class TestKernelMetaLayer:
    def test_poisoned_calibration_suppresses_signals(self) -> None:
        from tests.unit.decision.test_ledger import kernel, series

        fresh_kernel = kernel()
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        fresh = fresh_kernel.decide_series(series(40), context).unwrap()
        fresh_signals = sum(1 for o in fresh if o.action == "signal")
        assert fresh_signals >= 1

        poisoned = LearningState(
            alpha=(6.0,) * CHANNEL_COUNT, beta=(6.0,) * CHANNEL_COUNT,
            r_sum=(0.0,) * CHANNEL_COUNT, trades=(0.0,) * CHANNEL_COUNT,
            calibration_wins=(0.0,) * 10,
            calibration_trades=(0.0,) * 7 + (100.0, 100.0, 100.0),
        )
        from apex.core.time.clock import ManualClock as Clock_
        from apex.decision.kernel import CentralDecisionKernel

        guarded = CentralDecisionKernel(
            params=fresh_kernel._params,  # same tunables
            clock=Clock_(T0),
            learning=poisoned,
        )
        adjusted = guarded.decide_series(series(40), context).unwrap()
        adjusted_signals = sum(1 for o in adjusted if o.action == "signal")
        # Bins 7-9 observed ~1/102 wins: calibration collapses the 0.85
        # assessments below the threshold - no signal survives.
        assert adjusted_signals < fresh_signals


class TestProbabilityIcFold:
    def test_ic_needs_closes_and_stays_bounded(self) -> None:
        from apex.probability.engine import ConfluenceParams, ConfluenceProbabilityEngine

        from tests.unit.probability.test_probability import bullish_vector, snapshot

        engine = ConfluenceProbabilityEngine(
            params=ConfluenceParams(ic_length=50, ic_horizon=3),
            clock=ManualClock(T0),
        )
        without_close = [snapshot(i, bullish_vector()) for i in range(80)]
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        base = engine.assess_series(without_close, context).unwrap()

        from dataclasses import replace as dc_replace

        with_close = [
            dc_replace(item, close=100.0 + index * 0.5)
            for index, item in enumerate(without_close)
        ]
        adjusted = engine.assess_series(with_close, context).unwrap()
        assert len(base) == len(adjusted)
        # IC factors change the weight mix once warm - probabilities
        # remain valid and (in general) shift.
        for (_long_a, _), (long_b, _) in zip(base, adjusted, strict=True):
            assert 0.0 < long_b.probability.value < 1.0
        disabled = ConfluenceProbabilityEngine(
            params=ConfluenceParams(
                ic_length=50, ic_horizon=3, adaptive_weights_enabled=False
            ),
            clock=ManualClock(T0),
        )
        neutral = disabled.assess_series(with_close, context).unwrap()
        for (long_a, _), (long_b, _) in zip(base, neutral, strict=True):
            assert long_a.probability.value == pytest.approx(long_b.probability.value)


class TestPlugin:
    def test_manifest_requires_portfolio_and_execution(self) -> None:
        from apex.research.plugin import APEX_PLUGIN

        manifest = APEX_PLUGIN.manifest
        assert manifest.name == "research_platform"
        assert set(manifest.requires) == {"portfolio_platform", "execution_platform"}
