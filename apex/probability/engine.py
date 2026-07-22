"""Confluence probability engine - migrated from AICE (Phase 5).

Faithful port of the AICE confluence core (Book VI spec lines
2583-2790) over stored feature vectors:

- **Adaptive base weights** (lines 2632-2660): thirteen channel
  weights blended by trend confidence; the SMT weight grows in ranging
  and transition regimes with liquidity evidence and correlation
  quality; weights are normalized to sum to one.
- **Evidence fusion**: ``base = sum(w_i * ev_i)`` per side, plus the
  nine cross-channel interaction terms (lines 2722-2742) and the
  IFVG/BPR structure bonuses.
- **Penalty stack** (lines 2744-2761): opposing HTF context, HTF
  premium/discount against the side, compression, stale order blocks,
  stretched VWAP without a sweep, effort-vs-result against the candle,
  and a strong opposing SMT score.
- **Calibration** (lines 2769-2771): ``squash((raw - 0.45) * (5.4 +
  trend_conf * 1.2))``, clamped into [0.01, 0.99] (line 2843's final
  bounds).

Structure momentum (``struct_mom``, lines 2583-2586) folds over the
snapshot window: an EMA of the +/-1 break pulse derived from each
vector's BOS/CHoCH flags - which is why assessment is windowed.

Deferred to later phases (documented, AICE-gated or research-owned):
IC-based and meta-learning weight factors (``use_adaptive_weights``
off => factor 1.0), the meta probability calibrator ``f_calibrate``
(identity until the research platform measures outcomes, Phase 11),
probability smoothing (off by default in AICE), Kalman terms and the
crypto dominance bonus.

The confidence interval is APEX platform semantics (Book II 5.9
requires one; AICE has no interval concept): half-width scales with
the binary entropy of the estimate, replaced by measured calibration
error once the research platform lands.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from apex.contracts.engines import FeatureVectorSnapshot
from apex.core.context import MarketContext
from apex.core.exceptions import ApexError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import Entropy, Probability
from apex.core.validation import ensure_in_range, ensure_positive
from apex.domain.learning import CHANNEL_COUNT, LearningParams, LearningState
from apex.domain.probability import ConfidenceInterval, ProbabilityAssessment
from apex.features.calculations import clamp, correlation, ema, entropy01, squash
from apex.probability.evidence import (
    EvidenceChannels,
    compute_evidence,
    effort_result,
    flag,
    read,
)

_SOURCE = "apex.probability.engine"
SUBJECT_LONG = "trade.long"
SUBJECT_SHORT = "trade.short"

# Adaptive base weights (AICE lines 2632-2652): (intercept, trend slope)
# per channel w0..w12; the SMT weight (w11) is regime-composed below.
_BASE_WEIGHTS: tuple[tuple[float, float], ...] = (
    (0.12, 0.10),   # structure
    (0.20, -0.10),  # liquidity
    (0.15, -0.05),  # order blocks
    (0.10, -0.02),  # FVG
    (0.12, -0.06),  # zone
    (0.10, 0.0),    # candle DNA
    (0.08, 0.07),   # kinetic
    (0.08, 0.0),    # delta
    (0.03, 0.03),   # sequence
    (0.06, -0.03),  # trend
    (0.08, 0.0),    # MTF
)
_PROFILE_WEIGHT = 0.06
# SMT weight composition (lines 2646-2659).
_SMT_BASE = 0.035
_SMT_RANGING, _SMT_TRANSITION = 0.055, 0.030
_SMT_LIQUIDITY, _SMT_CORRELATION, _SMT_TREND = 0.045, 0.030, 0.030
_SMT_FLOOR, _SMT_CEIL = 0.010, 0.150
# Interaction weights (lines 2722-2742).
_INTER_LIQ_OB = 0.14
_INTER_LIQ_STRUCT = 0.14
_INTER_OB_FVG = 0.10
_INTER_STRUCT_MTF = 0.10
_INTER_SMT_LIQ = 0.09
_INTER_DELTA_STRUCT = 0.06
_INTER_DNA_KIN = 0.06
_INTER_IFVG_STRUCT = 0.05
_INTER_BPR_ZONE = 0.04
# Penalty stack (lines 2744-2761).
_PEN_HTF_OPPOSED = 0.25
_PEN_HTF_ZONE = 0.08
_PEN_COMPRESSION = 0.08
_PEN_STALE_OB = 0.07
_PEN_STRETCHED_VWAP = 0.07
_PEN_EFFORT = 0.04
_PEN_OPPOSING_SMT = 0.08
_STALE_FRESHNESS = 0.20
_STRETCHED_VWAP_Z = 2.0
_OPPOSING_SMT = 0.5


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfluenceParams:
    """Tunables of the confluence engine (AICE input defaults)."""

    momentum_length: int = 10
    # AICE learning inputs (Book VI lines 34-40), Phase 11.
    adaptive_weights_enabled: bool = True
    ic_length: int = 200
    ic_horizon: int = 12
    ic_strength: float = 0.35
    calibration_offset: float = 0.45
    calibration_gain_base: float = 5.4
    calibration_gain_slope: float = 1.2
    probability_floor: float = 0.01
    probability_ceiling: float = 0.99
    uncertainty_scale: float = 0.15

    def __post_init__(self) -> None:
        ensure_positive(self.momentum_length, "momentum_length")
        ensure_in_range(self.ic_length, 50, 1000, "ic_length")
        ensure_in_range(self.ic_horizon, 2, 100, "ic_horizon")
        ensure_in_range(self.ic_strength, 0.0, 1.0, "ic_strength")
        ensure_in_range(self.calibration_offset, 0.0, 1.0, "calibration_offset")
        ensure_positive(self.calibration_gain_base, "calibration_gain_base")
        ensure_in_range(self.calibration_gain_slope, 0.0, 10.0, "calibration_gain_slope")
        ensure_in_range(self.probability_floor, 0.0, 0.5, "probability_floor")
        ensure_in_range(self.probability_ceiling, 0.5, 1.0, "probability_ceiling")
        ensure_in_range(self.uncertainty_scale, 0.0, 0.5, "uncertainty_scale")


@dataclass(frozen=True, slots=True, kw_only=True)
class BarProbabilities:
    """Detailed per-bar output kept by the platform for persistence."""

    snapshot: FeatureVectorSnapshot
    long: ProbabilityAssessment
    short: ProbabilityAssessment
    channels: EvidenceChannels
    raw_long: float
    raw_short: float


class ConfluenceProbabilityEngine:
    """Fuses stored evidence into calibrated per-side probabilities."""

    def __init__(
        self,
        *,
        params: ConfluenceParams,
        clock: Clock,
        learning: LearningState | None = None,
        learning_params: LearningParams | None = None,
    ) -> None:
        self._params = params
        self._clock = clock
        # Accumulated closed-trade knowledge (research artifact); None
        # is the fresh chart - every factor 1.0 (Phase 11).
        self._learning = learning
        self._learning_params = learning_params or LearningParams()

    def assess_series(
        self,
        snapshots: Sequence[FeatureVectorSnapshot],
        context: MarketContext,
    ) -> Result[tuple[tuple[ProbabilityAssessment, ProbabilityAssessment], ...]]:
        """(long, short) assessments per snapshot (contract surface)."""
        detailed = self.assess_series_detailed(snapshots, context)
        if not detailed.ok:
            assert detailed.error is not None
            return Result.failure(detailed.error)
        pairs = tuple((bar.long, bar.short) for bar in detailed.unwrap())
        return Result.success(pairs)

    def assess_series_detailed(
        self,
        snapshots: Sequence[FeatureVectorSnapshot],
        context: MarketContext,
    ) -> Result[tuple[BarProbabilities, ...]]:
        """Full per-bar confluence detail for persistence and events."""
        try:
            bars = self._assess_all(list(snapshots))
        except ApexError as error:
            return Result.failure(error)
        return Result.success(tuple(bars))

    # --- Fold ---------------------------------------------------------------

    def _assess_all(
        self, snapshots: list[FeatureVectorSnapshot]
    ) -> list[BarProbabilities]:
        pulses = [self._pulse(snapshot.values) for snapshot in snapshots]
        momentum = ema(pulses, self._params.momentum_length)
        channel_series: list[EvidenceChannels] = []
        for index, snapshot in enumerate(snapshots):
            mom = momentum[index] or 0.0
            channel_series.append(compute_evidence(snapshot.values, mom))
        ic_factors = self._ic_factors(snapshots, channel_series)
        out: list[BarProbabilities] = []
        for index, snapshot in enumerate(snapshots):
            out.append(
                self._assess_bar(snapshot, channel_series[index], ic_factors[index])
            )
        return out

    def _ic_factors(
        self,
        snapshots: list[FeatureVectorSnapshot],
        channel_series: list[EvidenceChannels],
    ) -> list[tuple[float, ...]]:
        """Rolling IC weight factors per bar (AICE lines 2672-2687).

        ``f_ic``: the correlation, over ``ic_length`` bars, of each
        channel's edge lagged by the horizon against the completed
        horizon return - strictly causal (only finished forward
        windows inform a bar). Neutral (1.0) until closes exist and
        the window warms up, and when adaptive weights are off.
        """
        params = self._params
        count = len(snapshots)
        neutral = tuple(1.0 for _ in range(CHANNEL_COUNT))
        factors = [neutral] * count
        if not params.adaptive_weights_enabled or count <= params.ic_horizon:
            return factors
        closes = [snapshot.close for snapshot in snapshots]
        if any(close is None or close <= 0 for close in closes):
            return factors
        horizon = params.ic_horizon
        returns = [
            closes[i] / closes[i - horizon] - 1.0  # type: ignore[operator]
            for i in range(horizon, count)
        ]
        edges_by_channel = [
            [pairs[channel][0] - pairs[channel][1] for pairs in
             (bar.pairs() for bar in channel_series)]
            for channel in range(CHANNEL_COUNT)
        ]
        correlations = [
            correlation(edges[: count - horizon], returns, params.ic_length)
            for edges in edges_by_channel
        ]
        for i in range(horizon, count):
            row = []
            for channel in range(CHANNEL_COUNT):
                ic = correlations[channel][i - horizon]
                row.append(
                    clamp(1.0 + (ic or 0.0) * params.ic_strength, 0.65, 1.35)
                )
            factors[i] = tuple(row)
        return factors

    def _pulse(self, values: Mapping[str, float]) -> float:
        """AICE struct_pulse (line 2583): +1 up break, -1 down break."""
        if flag(values, "structure.bos_up") or flag(values, "structure.choch_up"):
            return 1.0
        if flag(values, "structure.bos_down") or flag(values, "structure.choch_down"):
            return -1.0
        return 0.0

    def _assess_bar(
        self,
        snapshot: FeatureVectorSnapshot,
        channels: EvidenceChannels,
        ic_factors: tuple[float, ...],
    ) -> BarProbabilities:
        vector = snapshot.values
        weights = self._weights(vector, channels, ic_factors)
        pairs = channels.pairs()
        base_long = sum(weight * pair[0] for weight, pair in zip(weights, pairs, strict=True))
        base_short = sum(weight * pair[1] for weight, pair in zip(weights, pairs, strict=True))
        inter_long, inter_short = self._interactions(vector, channels)
        pen_long, pen_short = self._penalties(vector, channels)
        raw_long = base_long + inter_long - pen_long
        raw_short = base_short + inter_short - pen_short
        gain = (
            self._params.calibration_gain_base
            + read(vector, "statistical.trend_confidence")
            * self._params.calibration_gain_slope
        )
        prob_long = self._calibrate(raw_long, gain)
        prob_short = self._calibrate(raw_short, gain)
        return BarProbabilities(
            snapshot=snapshot,
            long=self._assessment(SUBJECT_LONG, prob_long, len(vector)),
            short=self._assessment(SUBJECT_SHORT, prob_short, len(vector)),
            channels=channels,
            raw_long=raw_long,
            raw_short=raw_short,
        )

    def _weights(
        self,
        values: Mapping[str, float],
        channels: EvidenceChannels,
        ic_factors: tuple[float, ...],
    ) -> tuple[float, ...]:
        """Adaptive, normalized channel weights (AICE lines 2632-2718).

        Phase 11: each raw weight scales by the closed-trade channel
        factor (Beta posterior, ``f_feature_factor``) and the rolling
        IC factor before normalization - ``rw_i = bw_i x ff_i x icf_i``
        (lines 2689-2701).
        """
        trend_confidence = read(values, "statistical.trend_confidence")
        raw = [
            max(intercept + slope * trend_confidence, 0.0)
            for intercept, slope in _BASE_WEIGHTS
        ]
        is_trending = flag(values, "statistical.is_trending")
        is_ranging = flag(values, "statistical.is_ranging")
        smt_weight = clamp(
            _SMT_BASE
            + (_SMT_RANGING if is_ranging else 0.0)
            + (_SMT_TRANSITION if not is_trending and not is_ranging else 0.0)
            + max(channels.liquidity_long, channels.liquidity_short) * _SMT_LIQUIDITY
            + read(values, "smt.correlation_quality") * _SMT_CORRELATION
            - trend_confidence * _SMT_TREND,
            _SMT_FLOOR,
            _SMT_CEIL,
        )
        raw.append(smt_weight)
        raw.append(_PROFILE_WEIGHT)
        if self._params.adaptive_weights_enabled:
            raw = [
                weight
                * (
                    self._learning.channel_factor(index, self._learning_params)
                    if self._learning is not None
                    else 1.0
                )
                * ic_factors[index]
                for index, weight in enumerate(raw)
            ]
        total = sum(raw)
        return tuple(weight / total for weight in raw)

    def _interactions(
        self, values: Mapping[str, float], c: EvidenceChannels
    ) -> tuple[float, float]:
        """Cross-channel confluence bonuses (AICE lines 2722-2742)."""
        long_side = (
            c.liquidity_long * c.orderblock_long * _INTER_LIQ_OB
            + c.liquidity_long * c.structure_long * _INTER_LIQ_STRUCT
            + c.orderblock_long * c.fvg_long * _INTER_OB_FVG
            + c.structure_long * c.mtf_long * _INTER_STRUCT_MTF
            + c.smt_long * c.liquidity_long * _INTER_SMT_LIQ
            + c.delta_long * c.structure_long * _INTER_DELTA_STRUCT
            + c.dna_long * c.kinetic_long * _INTER_DNA_KIN
            + (1.0 if flag(values, "orderblocks.ifvg_bull") else 0.0)
            * c.structure_long
            * _INTER_IFVG_STRUCT
            + (1.0 if flag(values, "orderblocks.bpr_bull") else 0.0)
            * c.zone_long
            * _INTER_BPR_ZONE
        )
        short_side = (
            c.liquidity_short * c.orderblock_short * _INTER_LIQ_OB
            + c.liquidity_short * c.structure_short * _INTER_LIQ_STRUCT
            + c.orderblock_short * c.fvg_short * _INTER_OB_FVG
            + c.structure_short * c.mtf_short * _INTER_STRUCT_MTF
            + c.smt_short * c.liquidity_short * _INTER_SMT_LIQ
            + c.delta_short * c.structure_short * _INTER_DELTA_STRUCT
            + c.dna_short * c.kinetic_short * _INTER_DNA_KIN
            + (1.0 if flag(values, "orderblocks.ifvg_bear") else 0.0)
            * c.structure_short
            * _INTER_IFVG_STRUCT
            + (1.0 if flag(values, "orderblocks.bpr_bear") else 0.0)
            * c.zone_short
            * _INTER_BPR_ZONE
        )
        return long_side, short_side

    def _penalties(
        self, values: Mapping[str, float], c: EvidenceChannels
    ) -> tuple[float, float]:
        """Opposing-context penalty stack (AICE lines 2744-2761)."""
        vwap_z = read(values, "volume.vwap_deviation_z")
        compression = flag(values, "volume.compression")
        effort = effort_result(values)
        direction = read(values, "statistical.direction")
        long_side = (
            (_PEN_HTF_OPPOSED if flag(values, "htf.bear_context") else 0.0)
            + (_PEN_HTF_ZONE if flag(values, "htf.in_premium") else 0.0)
            + (_PEN_COMPRESSION if compression else 0.0)
            + (
                _PEN_STALE_OB
                if read(values, "orderblocks.ob_long_confidence") > 0
                and read(values, "orderblocks.ob_long_freshness") < _STALE_FRESHNESS
                else 0.0
            )
            + (
                _PEN_STRETCHED_VWAP
                if vwap_z > _STRETCHED_VWAP_Z and not flag(values, "structure.sweep_low")
                else 0.0
            )
            + (_PEN_EFFORT if effort and direction < 0 else 0.0)
            + (_PEN_OPPOSING_SMT if c.smt_short > _OPPOSING_SMT else 0.0)
        )
        short_side = (
            (_PEN_HTF_OPPOSED if flag(values, "htf.bull_context") else 0.0)
            + (_PEN_HTF_ZONE if flag(values, "htf.in_discount") else 0.0)
            + (_PEN_COMPRESSION if compression else 0.0)
            + (
                _PEN_STALE_OB
                if read(values, "orderblocks.ob_short_confidence") > 0
                and read(values, "orderblocks.ob_short_freshness") < _STALE_FRESHNESS
                else 0.0
            )
            + (
                _PEN_STRETCHED_VWAP
                if vwap_z < -_STRETCHED_VWAP_Z
                and not flag(values, "structure.sweep_high")
                else 0.0
            )
            + (_PEN_EFFORT if effort and direction > 0 else 0.0)
            + (_PEN_OPPOSING_SMT if c.smt_long > _OPPOSING_SMT else 0.0)
        )
        return long_side, short_side

    def _calibrate(self, raw: float, gain: float) -> float:
        """AICE lines 2769-2771 + the final clamp (line 2843)."""
        params = self._params
        probability = squash((raw - params.calibration_offset) * gain)
        return clamp(probability, params.probability_floor, params.probability_ceiling)

    def _assessment(
        self, subject: str, probability: float, vector_size: int
    ) -> ProbabilityAssessment:
        dispersion = entropy01(probability)
        half_width = self._params.uncertainty_scale * dispersion
        lower = clamp(probability - half_width, 0.0, 1.0)
        upper = clamp(probability + half_width, 0.0, 1.0)
        return ProbabilityAssessment(
            created_at=self._clock.now(),
            subject=subject,
            probability=Probability(probability),
            distribution={
                "success": Probability(probability),
                "failure": Probability(1.0 - probability),
            },
            confidence_interval=ConfidenceInterval(
                lower=Probability(lower), upper=Probability(upper)
            ),
            entropy=Entropy(dispersion),
            sample_size=vector_size,
        )
