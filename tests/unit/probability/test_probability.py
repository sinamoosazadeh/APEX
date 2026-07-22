"""Probability platform: evidence channels, confluence, calibration, store."""

import asyncio
from pathlib import Path

import pytest
from apex.contracts.engines import FeatureVectorSnapshot, IProbabilityEngine
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.probability.engine import (
    ConfluenceParams,
    ConfluenceProbabilityEngine,
)
from apex.probability.evidence import compute_evidence
from apex.probability.store import AssessmentRecord, SqliteProbabilityRepository

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

PARAMS = ConfluenceParams()


def bullish_vector() -> dict[str, float]:
    """A coherent, strongly bullish confluence state."""
    return {
        "structure.bos_up": 1.0,
        "structure.choch_up": 0.0,
        "structure.bos_down": 0.0,
        "structure.choch_down": 0.0,
        "structure.is_displacement": 1.0,
        "structure.break_quality": 0.9,
        "structure.trend_direction": 1.0,
        "structure.sweep_low": 1.0,
        "structure.sweep_high": 0.0,
        "structure.in_discount": 1.0,
        "structure.in_premium": 0.0,
        "structure.in_ote_long": 1.0,
        "structure.in_ote_short": 0.0,
        "structure.internal_bias": 1.0,
        "structure.external_bias": 1.0,
        "liquidity.sweep_low_efficiency": 0.8,
        "liquidity.sweep_high_efficiency": 0.0,
        "liquidity.resting_low": 0.6,
        "liquidity.resting_high": 0.1,
        "liquidity.stop_hunt_low": 1.0,
        "liquidity.stop_hunt_high": 0.0,
        "liquidity.inducement_long": 1.0,
        "liquidity.inducement_short": 0.0,
        "orderblocks.ob_long_confidence": 0.7,
        "orderblocks.ob_short_confidence": 0.05,
        "orderblocks.ob_long_freshness": 0.9,
        "orderblocks.ob_short_freshness": 0.9,
        "orderblocks.fvg_long_confidence": 0.6,
        "orderblocks.fvg_short_confidence": 0.05,
        "orderblocks.ifvg_bull": 1.0,
        "orderblocks.ifvg_bear": 0.0,
        "orderblocks.bpr_bull": 1.0,
        "orderblocks.bpr_bear": 0.0,
        "volume.rvol": 1.2,
        "volume.aggression": 0.6,
        "volume.absorption_buy": 1.0,
        "volume.absorption_sell": 0.0,
        "volume.selling_climax": 1.0,
        "volume.buying_climax": 0.0,
        "volume.expansion": 1.0,
        "volume.compression": 0.0,
        "volume.narrow_range": 0.0,
        "volume.vwap_deviation_atr": 0.5,
        "volume.vwap_deviation_z": -1.5,
        "volume.momentum_bull": 1.0,
        "volume.momentum_bear": 0.0,
        "volume.momentum_slope": 0.8,
        "volume.above_poc": 1.0,
        "volume.poc_acceptance": 0.8,
        "volume.poc_distance_atr": 0.5,
        "htf.bull_context": 1.0,
        "htf.bear_context": 0.0,
        "htf.in_discount": 1.0,
        "htf.in_premium": 0.0,
        "htf.macro1_bias": 1.0,
        "htf.macro2_bias": 1.0,
        "htf.alignment": 2.0,
        "smt.bull_confidence": 0.6,
        "smt.bear_confidence": 0.05,
        "smt.correlation_quality": 0.7,
        "statistical.trend_confidence": 0.7,
        "statistical.is_trending": 1.0,
        "statistical.is_ranging": 0.0,
        "statistical.dna_bull": 0.7,
        "statistical.dna_bear": 0.2,
        "statistical.kinetic_long": 0.6,
        "statistical.kinetic_short": 0.1,
        "statistical.sequence_bull_bias": 0.8,
        "statistical.sequence_bear_bias": 0.0,
        "statistical.direction_flip_bull": 1.0,
        "statistical.direction_flip_bear": 0.0,
        "statistical.direction": 1.0,
    }


def snapshot(index: int, vector: dict[str, float]) -> FeatureVectorSnapshot:
    return FeatureVectorSnapshot(
        bar_open_time=T0.add_ms(index * H1_MS), values=vector
    )


def engine() -> ConfluenceProbabilityEngine:
    return ConfluenceProbabilityEngine(params=PARAMS, clock=ManualClock(T0))


def context() -> MarketContext:
    return MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)


class TestEvidenceChannels:
    def test_passthrough_channels(self) -> None:
        channels = compute_evidence(bullish_vector(), 0.0)
        assert channels.orderblock_long == 0.7
        assert channels.fvg_long == 0.6
        assert channels.dna_long == 0.7
        assert channels.kinetic_long == 0.6
        assert channels.smt_long == 0.6

    def test_zone_channel_formula(self) -> None:
        # discount 0.40 + OTE 0.30 + HTF discount 0.20 + stretched VWAP 0.10.
        channels = compute_evidence(bullish_vector(), 0.0)
        assert channels.zone_long == pytest.approx(1.0)
        assert channels.zone_short == pytest.approx(0.0)

    def test_mtf_channel_full_alignment(self) -> None:
        channels = compute_evidence(bullish_vector(), 0.0)
        assert channels.mtf_long == pytest.approx(1.0)
        assert channels.mtf_short == pytest.approx(0.0)

    def test_liquidity_gated_by_sweep(self) -> None:
        vector = bullish_vector()
        vector["structure.sweep_low"] = 0.0
        vector["volume.expansion"] = 0.0
        channels = compute_evidence(vector, 0.0)
        assert channels.liquidity_long == 0.0

    def test_structure_momentum_lifts_the_long_side(self) -> None:
        flat = compute_evidence(bullish_vector(), 0.0)
        boosted = compute_evidence(bullish_vector(), 0.8)
        assert boosted.structure_long > flat.structure_long
        assert boosted.structure_short == flat.structure_short

    def test_empty_vector_is_fully_neutral(self) -> None:
        channels = compute_evidence({}, 0.0)
        for long_side, short_side in channels.pairs():
            assert long_side <= 0.5 and short_side <= 0.5


class TestConfluenceEngine:
    def test_bullish_state_favors_the_long_side(self) -> None:
        result = engine().assess_series([snapshot(0, bullish_vector())], context())
        ((long, short),) = result.unwrap()
        assert long.probability.value > 0.75
        assert short.probability.value < 0.25
        assert long.probability.value > short.probability.value

    def test_assessment_contract_shape(self) -> None:
        result = engine().assess_series([snapshot(0, bullish_vector())], context())
        ((long, short),) = result.unwrap()
        for assessment in (long, short):
            total = sum(p.value for p in assessment.distribution.values())
            assert total == pytest.approx(1.0)
            assert assessment.confidence_interval.contains(assessment.probability)
            assert 0.0 <= assessment.entropy.value <= 1.0
            assert PARAMS.probability_floor <= assessment.probability.value
            assert assessment.probability.value <= PARAMS.probability_ceiling
        assert long.subject == "trade.long"
        assert short.subject == "trade.short"

    def test_neutral_vector_reads_below_even_odds(self) -> None:
        result = engine().assess_series([snapshot(0, {})], context())
        ((long, short),) = result.unwrap()
        # raw 0 vs the 0.45 offset: squash(-2.43) ~ 0.081.
        assert long.probability.value < 0.15
        assert short.probability.value < 0.15

    def test_break_history_builds_structure_momentum(self) -> None:
        quiet = {"structure.trend_direction": 1.0}
        breaking = {"structure.bos_up": 1.0, "structure.trend_direction": 1.0}
        history = [snapshot(i, dict(breaking)) for i in range(12)]
        history.append(snapshot(12, dict(quiet)))
        cold = engine().assess_series([snapshot(0, dict(quiet))], context())
        warm = engine().assess_series(history, context())
        cold_prob = cold.unwrap()[0][0].probability.value
        warm_prob = warm.unwrap()[-1][0].probability.value
        assert warm_prob > cold_prob

    def test_htf_opposition_penalizes_the_long_side(self) -> None:
        favorable = engine().assess_series([snapshot(0, bullish_vector())], context())
        opposed_vector = bullish_vector()
        opposed_vector["htf.bull_context"] = 0.0
        opposed_vector["htf.bear_context"] = 1.0
        opposed = engine().assess_series([snapshot(0, opposed_vector)], context())
        assert (
            opposed.unwrap()[0][0].probability.value
            < favorable.unwrap()[0][0].probability.value
        )

    def test_deterministic(self) -> None:
        first = engine().assess_series([snapshot(0, bullish_vector())], context())
        second = engine().assess_series([snapshot(0, bullish_vector())], context())
        assert (
            first.unwrap()[0][0].probability.value
            == second.unwrap()[0][0].probability.value
        )

    def test_engine_satisfies_the_contract(self) -> None:
        assert isinstance(engine(), IProbabilityEngine)

    def test_invalid_params_are_rejected(self) -> None:
        with pytest.raises(Exception, match="momentum_length"):
            ConfluenceParams(momentum_length=0)


class TestAssessmentStore:
    def test_roundtrip_and_idempotency(self, tmp_path: Path) -> None:
        asyncio.run(self._roundtrip(tmp_path))

    async def _roundtrip(self, tmp_path: Path) -> None:
        repository = SqliteProbabilityRepository(
            database_path=tmp_path / "probability.sqlite"
        )
        await repository.open()
        try:
            record = AssessmentRecord(
                exchange="toobit",
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                bar_open_time=T0,
                side="long",
                probability=0.82,
                lower_bound=0.72,
                upper_bound=0.92,
                entropy=0.68,
                raw_score=0.61,
                sample_size=133,
                channels={"structure_long": 0.9},
                computed_at=T0,
            )
            assert await repository.upsert([record]) == 1
            assert await repository.upsert([record]) == 1  # idempotent
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 1
            rows = await repository.get_range(
                "toobit",
                "BTCUSDT",
                Timeframe.H1,
                start=Timestamp(epoch_ms=0),
                end=Timestamp(epoch_ms=10**14),
            )
            assert rows == [record]
        finally:
            await repository.close()
