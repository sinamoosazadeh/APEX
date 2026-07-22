"""Central Decision Kernel - migrated from AICE (Phase 6, Book I ch. 9).

The single decision authority: folds persisted probability assessments
and feature vectors into fired signals, vetoed readiness records and
stand-asides, porting the AICE gate/timing stack (Book VI spec lines
2845-3115):

- **Contributors** (lines 2848-2877): per-channel evidence counts with
  the AICE thresholds; ``thin_evidence`` against the minimum.
- **Uncertainty** (line 2882): ambiguity between the sides, return
  entropy, transition regime, thin evidence and volatility clustering.
- **Expectancy** (lines 2887-2903): target room against the macro
  extreme (na-branch 1.0), rr quality, ``expected_R = p * rr - (1-p)
  - fees`` and the signal confidence composite.
- **Profile gates** (lines 2950-2974): regime-adjusted probability
  threshold and uncertainty ceiling, RVOL/ATR-percent/warmup gates,
  HTF permission, contributor minimum, entropy standby with catalyst
  override, the failure-risk oracle, bar quality, the expectancy gate,
  the L/S probability edge and confidence comparison.
- **Signal clustering** (lines 2976-3006): cooldown bars plus the
  13-channel cosine-similarity cooldown against the last fired signal.
- **Execution timing** (lines 3018-3086): Immediate, Trigger Candle,
  or the Retest + Micro BOS pending state machine (pullback then
  trigger/micro-BOS confirmation within the pending window).
- **Entry construction** (lines 3092-3115): entry at close, ATR or
  Structure Hybrid stop (protected swing, AICE's OB-bottom variant
  arrives with the execution-phase zone store), and the three
  R-multiple targets with the macro-extreme liquidity resolver.

Deferred along AICE gates / later phases (documented): position
flatness (portfolio platform - no positions exist yet), the virtual
equity guard (requires trade history; passes below its minimum trade
count exactly like a fresh AICE chart), crypto-context permissions and
the Kalman filter.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from math import sqrt

from apex.contracts.engines import DecisionSnapshot
from apex.core.context import MarketContext
from apex.core.enums import Direction
from apex.core.exceptions import ApexError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import (
    Confidence,
    ExpectedReturn,
    Price,
    Probability,
    RiskReward,
)
from apex.core.validation import ensure_in_range, ensure_positive
from apex.decision.setups import classify_long, classify_short
from apex.domain.market import Bar
from apex.domain.signal import PriceZone, Signal
from apex.features.calculations import clamp, ema, rolling_extremes, session_vwap, wilder_atr
from apex.probability.evidence import flag, read

_SOURCE = "apex.decision.kernel"

# Contributor thresholds per channel (AICE lines 2849-2877), in the
# w0..w12 order: struct, liq, ob, fvg, zone, dna, kin, delta, seq,
# trend, mtf, smt, profile.
_CONTRIBUTOR_THRESHOLDS: tuple[float, ...] = (
    0.35, 0.35, 0.25, 0.25, 0.35, 0.45, 0.35, 0.35, 0.35, 0.35, 0.45, 0.25, 0.35,
)
_CHANNELS: tuple[str, ...] = (
    "structure", "liquidity", "orderblock", "fvg", "zone", "dna",
    "kinetic", "delta", "sequence", "trend", "mtf", "smt", "profile",
)
# Uncertainty composition (line 2882).
_UNC_AMBIGUITY, _UNC_ENTROPY, _UNC_TRANSITION = 0.38, 0.28, 0.15
_UNC_THIN, _UNC_CLUSTER = 0.12, 0.07
# rr quality shape (lines 2892-2894).
_RR_BASE, _RR_ROOM, _RR_CATALYST, _RR_UNCERTAINTY = 0.75, 0.20, 0.15, 0.10
_RR_FLOOR, _RR_CEIL = 0.50, 1.30
_ROOM_CAP = 1.5
_TP3_FACTOR = 1.50
# Profile adjustments (lines 2950-2953).
_PROFILE_SHIFT = 0.07
_UNC_SHIFT = 0.10
_THRESH_TRANSITION, _THRESH_COMPRESSION, _THRESH_EXPANSION = 0.03, 0.02, 0.01
_THRESH_FLOOR, _THRESH_CEIL = 0.40, 0.98
_UNC_FLOOR, _UNC_CEIL = 0.05, 0.95
# Oracle composition (lines 2943-2944).
_ORACLE_UNCERTAINTY, _ORACLE_ENTROPY, _ORACLE_THIN = 0.38, 0.25, 0.15
_ORACLE_EXPECTANCY = 0.10
# Entropy standby catalyst override (lines 2958-2959).
_CATALYST_OVERRIDE = 0.75
# Bar quality body fraction (lines 2965-2966).
_QUALITY_BODY_FRACTION = 0.08
# Trigger candle body fraction (line 3010).
_TRIGGER_BODY_FRACTION = 0.10
# Pending relaxations (lines 3049, 3063).
_PENDING_THRESHOLD_RELIEF = 0.03
_PENDING_EXPECTANCY_FACTOR = 0.50
# Structure Hybrid stop shape (lines 3095-3103).
_STOP_BUFFER_ATR = 0.15
_STOP_MAX_FACTOR = 1.60
_STOP_MIN_ATR = 0.35
_TP1_FACTOR = 0.50

TIMING_IMMEDIATE = "immediate"
TIMING_TRIGGER = "trigger_candle"
TIMING_RETEST = "retest_micro_bos"
STOP_ATR = "atr"
STOP_STRUCTURE_HYBRID = "structure_hybrid"


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionParams:
    """Tunables of the decision kernel (AICE input defaults)."""

    probability_threshold: float = 0.62
    probability_edge: float = 0.03
    uncertainty_maximum: float = 0.45
    execution_profile_shift: float = 0.0
    execution_timing: str = TIMING_RETEST
    minimum_contributors: int = 3
    cooldown_bars: int = 24
    rvol_gate_enabled: bool = True
    rvol_cutoff: float = 1.5
    minimum_atr_percent: float = 0.01
    maximum_atr_percent: float = 5.0
    entropy_standby_enabled: bool = True
    entropy_maximum: float = 0.78
    oracle_enabled: bool = True
    oracle_failure_maximum: float = 0.72
    expectancy_gate_enabled: bool = True
    minimum_expected_r: float = 0.10
    minimum_expected_edge_r: float = 0.03
    fee_slippage_r: float = 0.02
    stop_atr_multiple: float = 2.0
    target_atr_multiple: float = 3.5
    stop_model: str = STOP_STRUCTURE_HYBRID
    liquidity_targets_enabled: bool = True
    similarity_cooldown_enabled: bool = True
    similarity_threshold: float = 0.88
    similarity_cooldown_bars: int = 60
    pending_maximum_bars: int = 12
    micro_bos_length: int = 3
    trigger_close_location: float = 0.62
    atr_length: int = 14
    ema_length: int = 20
    structure_pivot_lookback: int = 8

    def __post_init__(self) -> None:
        ensure_in_range(self.probability_threshold, 0.4, 0.99, "probability_threshold")
        ensure_in_range(self.probability_edge, 0.0, 0.5, "probability_edge")
        ensure_in_range(self.uncertainty_maximum, 0.05, 0.95, "uncertainty_maximum")
        ensure_positive(self.minimum_contributors, "minimum_contributors")
        ensure_positive(self.rvol_cutoff, "rvol_cutoff")
        ensure_in_range(self.entropy_maximum, 0.4, 0.98, "entropy_maximum")
        ensure_in_range(self.oracle_failure_maximum, 0.4, 0.95, "oracle_failure_maximum")
        ensure_positive(self.stop_atr_multiple, "stop_atr_multiple")
        ensure_positive(self.target_atr_multiple, "target_atr_multiple")
        ensure_positive(self.pending_maximum_bars, "pending_maximum_bars")
        ensure_positive(self.micro_bos_length, "micro_bos_length")
        ensure_in_range(self.trigger_close_location, 0.5, 0.95, "trigger_close_location")
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.ema_length, "ema_length")
        ensure_positive(self.structure_pivot_lookback, "structure_pivot_lookback")
        if self.execution_timing not in (TIMING_IMMEDIATE, TIMING_TRIGGER, TIMING_RETEST):
            raise ApexError("unknown execution timing", code="DEC-001")
        if self.stop_model not in (STOP_ATR, STOP_STRUCTURE_HYBRID):
            raise ApexError("unknown stop model", code="DEC-002")

    @property
    def base_risk_reward(self) -> float:
        """AICE ``base_rr = tp_mult / sl_mult`` (line 2887)."""
        return self.target_atr_multiple / self.stop_atr_multiple


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionOutcome:
    """One bar's decision: signal, armed pending, veto or stand-aside."""

    bar_open_ms: int
    action: str  # "signal" | "pending" | "veto" | "stand_aside"
    direction: Direction
    setup: str
    signal: Signal | None
    probability: float
    uncertainty: float
    expected_r: float
    contributors: int
    failed_gates: tuple[str, ...]


@dataclass(slots=True)
class _SideState:
    """Per-side derived figures for one bar."""

    probability: float
    contributors: int
    catalyst: float
    expected_r: float
    confidence: float
    ready: bool
    failed: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _KernelState:
    """AICE ``var`` block: cooldowns, similarity memory, pending setup."""

    last_signal_bar: int = -10_000
    last_similar_bar: int = -10_000
    last_direction: int = 0
    last_channels: tuple[float, ...] | None = None
    pending_direction: int = 0
    pending_bar: int = 0
    pending_pullback: bool = False
    pending_setup: str = ""


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """AICE ``f_cos13``: cosine similarity, 0 on degenerate norms."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    n1 = sum(x * x for x in a)
    n2 = sum(y * y for y in b)
    if n1 > 0 and n2 > 0:
        return dot / (sqrt(n1) * sqrt(n2))
    return 0.0


class CentralDecisionKernel:
    """Folds assessments and vectors into audited trade decisions."""

    def __init__(self, *, params: DecisionParams, clock: Clock) -> None:
        self._params = params
        self._clock = clock

    def decide_series(
        self,
        snapshots: Sequence[DecisionSnapshot],
        context: MarketContext,
    ) -> Result[tuple[DecisionOutcome, ...]]:
        """One outcome per snapshot, folding kernel state in order."""
        try:
            outcomes = self._decide_all(list(snapshots), context)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(tuple(outcomes))

    # --- Fold ---------------------------------------------------------------

    def _decide_all(
        self, snapshots: list[DecisionSnapshot], context: MarketContext
    ) -> list[DecisionOutcome]:
        bars = [snapshot.bar for snapshot in snapshots]
        atr = wilder_atr(bars, self._params.atr_length)
        vwap = session_vwap(bars)
        ema20 = ema([float(bar.close.value) for bar in bars], self._params.ema_length)
        state = _KernelState()
        outcomes: list[DecisionOutcome] = []
        for index in range(len(snapshots)):
            outcomes.append(
                self._decide_bar(
                    state, snapshots, index, context,
                    atr=atr[index], vwap=vwap[index], ema20=ema20[index],
                )
            )
        return outcomes

    def _decide_bar(
        self,
        state: _KernelState,
        snapshots: list[DecisionSnapshot],
        index: int,
        context: MarketContext,
        *,
        atr: float | None,
        vwap: float | None,
        ema20: float | None,
    ) -> DecisionOutcome:
        snapshot = snapshots[index]
        uncertainty = self._uncertainty(snapshot)
        long_side = self._side(snapshot, index, uncertainty, atr, bullish=True)
        short_side = self._side(snapshot, index, uncertainty, atr, bullish=False)
        shared = self._shared_gates(snapshot, index, atr)
        self._apply_shared(long_side, shared)
        self._apply_shared(short_side, shared)
        self._apply_cluster_gates(state, snapshot, index, long_side, short_side)
        fired_direction, from_pending = self._timing(
            state, snapshots, index, long_side, short_side,
            atr=atr, vwap=vwap, ema20=ema20,
        )
        previous_compression = index >= 1 and flag(
            snapshots[index - 1].vector, "volume.compression"
        )
        return self._outcome(
            state, snapshot, index, fired_direction, from_pending,
            long_side, short_side, uncertainty, atr,
            previous_compression=previous_compression,
        )

    # --- Derived figures ------------------------------------------------------

    def _contributors(self, channels: Mapping[str, float], suffix: str) -> int:
        count = 0
        for name, threshold in zip(_CHANNELS, _CONTRIBUTOR_THRESHOLDS, strict=True):
            if read(channels, f"{name}_{suffix}") > threshold:
                count += 1
        return count

    def _uncertainty(self, snapshot: DecisionSnapshot) -> float:
        """AICE line 2882 over the persisted state."""
        vector = snapshot.vector
        params = self._params
        contributors = max(
            self._contributors(snapshot.channels, "long")
            if snapshot.probability_long >= snapshot.probability_short
            else self._contributors(snapshot.channels, "short"),
            0,
        )
        thin = contributors < params.minimum_contributors
        ambiguity = 1.0 - abs(snapshot.probability_long - snapshot.probability_short)
        is_trending = flag(vector, "statistical.is_trending")
        is_ranging = flag(vector, "statistical.is_ranging")
        transition = not is_trending and not is_ranging
        return clamp(
            _UNC_AMBIGUITY * ambiguity
            + _UNC_ENTROPY * read(vector, "statistical.return_entropy")
            + _UNC_TRANSITION * (1.0 if transition else 0.0)
            + _UNC_THIN * (1.0 if thin else 0.0)
            + _UNC_CLUSTER * max(read(vector, "statistical.volatility_clustering"), 0.0),
            0.0,
            1.0,
        )

    def _side(
        self,
        snapshot: DecisionSnapshot,
        index: int,
        uncertainty: float,
        atr: float | None,
        *,
        bullish: bool,
    ) -> _SideState:
        params = self._params
        suffix = "long" if bullish else "short"
        channels = snapshot.channels
        probability = snapshot.probability_long if bullish else snapshot.probability_short
        catalyst = max(
            read(channels, f"structure_{suffix}"),
            read(channels, f"liquidity_{suffix}"),
            read(channels, f"orderblock_{suffix}"),
            read(channels, f"fvg_{suffix}"),
        )
        close = float(snapshot.bar.close.value)
        room = 1.0
        target = snapshot.macro_high if bullish else snapshot.macro_low
        if target is not None and atr is not None and atr > 0:
            distance = (target - close) if bullish else (close - target)
            if distance > 0:
                room = distance / max(atr * params.target_atr_multiple, 1e-9)
        rr_quality = clamp(
            _RR_BASE
            + _RR_ROOM * clamp(room, 0.0, _ROOM_CAP)
            + _RR_CATALYST * catalyst
            - _RR_UNCERTAINTY * uncertainty,
            _RR_FLOOR,
            _RR_CEIL,
        )
        expected_rr = params.base_risk_reward * _TP3_FACTOR * rr_quality
        expected_r = (
            probability * expected_rr - (1.0 - probability) - params.fee_slippage_r
        )
        confidence = probability * (1.0 - uncertainty) * clamp(
            (expected_r + 1.0) / 2.0, 0.0, 1.0
        )
        side = _SideState(
            probability=probability,
            contributors=self._contributors(channels, suffix),
            catalyst=catalyst,
            expected_r=expected_r,
            confidence=confidence,
            ready=False,
        )
        self._readiness(side, snapshot, uncertainty, bullish=bullish)
        return side

    def _readiness(
        self,
        side: _SideState,
        snapshot: DecisionSnapshot,
        uncertainty: float,
        *,
        bullish: bool,
    ) -> None:
        """AICE ready_long/short (lines 2973-2974) minus shared gates."""
        params = self._params
        vector = snapshot.vector
        threshold, unc_ceiling = self._profile(vector)
        if side.probability < threshold:
            side.failed.append("probability_threshold")
        if uncertainty > unc_ceiling:
            side.failed.append("uncertainty_ceiling")
        alignment = read(vector, "htf.alignment")
        if (alignment < 0 if bullish else alignment > 0):
            side.failed.append("htf_permission")
        if side.contributors < params.minimum_contributors:
            side.failed.append("minimum_contributors")
        entropy_standby = (
            params.entropy_standby_enabled
            and read(vector, "statistical.market_entropy") > params.entropy_maximum
        )
        if entropy_standby and side.catalyst < _CATALYST_OVERRIDE:
            side.failed.append("entropy_standby")
        if params.oracle_enabled and self._oracle(snapshot, uncertainty, side) > (
            params.oracle_failure_maximum
        ):
            side.failed.append("failure_oracle")
        if not self._bar_quality(snapshot.bar, vector, bullish=bullish):
            side.failed.append("bar_quality")
        opposing = (
            snapshot.probability_short if bullish else snapshot.probability_long
        )
        if params.expectancy_gate_enabled and side.expected_r < params.minimum_expected_r:
            side.failed.append("expectancy_floor")
        if side.probability - opposing < params.probability_edge:
            side.failed.append("probability_edge")
        side.ready = not side.failed

    def _profile(self, vector: Mapping[str, float]) -> tuple[float, float]:
        """Regime-adjusted threshold and uncertainty ceiling."""
        params = self._params
        is_trending = flag(vector, "statistical.is_trending")
        is_ranging = flag(vector, "statistical.is_ranging")
        transition = not is_trending and not is_ranging
        compression = flag(vector, "volume.compression")
        expansion = flag(vector, "volume.expansion")
        threshold = clamp(
            params.probability_threshold
            + params.execution_profile_shift
            + (_THRESH_TRANSITION if transition else 0.0)
            + (_THRESH_COMPRESSION if compression else 0.0)
            - (_THRESH_EXPANSION if is_trending and expansion else 0.0),
            _THRESH_FLOOR,
            _THRESH_CEIL,
        )
        ceiling = clamp(
            params.uncertainty_maximum - params.execution_profile_shift * (
                _UNC_SHIFT / _PROFILE_SHIFT
            ) * (1.0 if params.execution_profile_shift else 0.0),
            _UNC_FLOOR,
            _UNC_CEIL,
        )
        return threshold, ceiling

    def _oracle(
        self, snapshot: DecisionSnapshot, uncertainty: float, side: _SideState
    ) -> float:
        """Failure-risk oracle (lines 2943-2944); guard terms follow
        their AICE gates (no trades yet, crypto context deferred)."""
        thin = side.contributors < self._params.minimum_contributors
        return clamp(
            _ORACLE_UNCERTAINTY * uncertainty
            + _ORACLE_ENTROPY * read(snapshot.vector, "statistical.market_entropy")
            + (_ORACLE_THIN if thin else 0.0)
            + (_ORACLE_EXPECTANCY if side.expected_r < 0 else 0.0),
            0.0,
            1.0,
        )

    def _bar_quality(
        self, bar: Bar, vector: Mapping[str, float], *, bullish: bool
    ) -> bool:
        """AICE bar_quality (lines 2965-2966)."""
        close = float(bar.close.value)
        open_ = float(bar.open.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        spread = high - low
        body = abs(close - open_)
        body_fraction = body / spread if spread > 0 else 0.0
        wick = (min(open_, close) - low) if bullish else (high - max(open_, close))
        sweep = flag(vector, "structure.sweep_low" if bullish else "structure.sweep_high")
        return (
            body_fraction >= _QUALITY_BODY_FRACTION
            or flag(vector, "structure.is_displacement")
            or sweep
            or wick > body
        )

    # --- Shared and clustering gates -------------------------------------------

    def _shared_gates(
        self, snapshot: DecisionSnapshot, index: int, atr: float | None
    ) -> list[str]:
        """base_gate (line 2971): RVOL, ATR percent; bars are confirmed
        upstream and flatness/warmup are documented deferrals."""
        params = self._params
        vector = snapshot.vector
        failed: list[str] = []
        if (
            params.rvol_gate_enabled
            and flag(vector, "volume.volume_available")
            and read(vector, "volume.rvol") < params.rvol_cutoff
        ):
            failed.append("rvol_gate")
        close = float(snapshot.bar.close.value)
        atr_percent = (atr / close * 100.0) if atr is not None and close > 0 else 0.0
        if not (params.minimum_atr_percent <= atr_percent <= params.maximum_atr_percent):
            failed.append("atr_band")
        return failed

    def _apply_shared(self, side: _SideState, failed: list[str]) -> None:
        if failed:
            side.failed.extend(failed)
            side.ready = False

    def _apply_cluster_gates(
        self,
        state: _KernelState,
        snapshot: DecisionSnapshot,
        index: int,
        long_side: _SideState,
        short_side: _SideState,
    ) -> None:
        params = self._params
        if index - state.last_signal_bar < params.cooldown_bars:
            for side in (long_side, short_side):
                side.failed.append("cooldown")
                side.ready = False
        if not params.similarity_cooldown_enabled or state.last_channels is None:
            return
        for side, direction, suffix in (
            (long_side, 1, "long"), (short_side, -1, "short"),
        ):
            if state.last_direction != direction:
                continue
            if index - state.last_similar_bar >= params.similarity_cooldown_bars:
                continue
            current = tuple(
                read(snapshot.channels, f"{name}_{suffix}") for name in _CHANNELS
            )
            if _cosine(current, state.last_channels) >= params.similarity_threshold:
                side.failed.append("similarity_cooldown")
                side.ready = False

    # --- Execution timing --------------------------------------------------------

    def _timing(
        self,
        state: _KernelState,
        snapshots: list[DecisionSnapshot],
        index: int,
        long_side: _SideState,
        short_side: _SideState,
        *,
        atr: float | None,
        vwap: float | None,
        ema20: float | None,
    ) -> tuple[int, bool]:
        """Fired direction (+1/-1/0) and whether it came from pending."""
        params = self._params
        if params.execution_timing == TIMING_IMMEDIATE:
            return self._resolve_immediate(long_side, short_side), False
        snapshot = snapshots[index]
        trigger_long = self._trigger(snapshot, bullish=True)
        trigger_short = self._trigger(snapshot, bullish=False)
        if params.execution_timing == TIMING_TRIGGER:
            fired_long = long_side.ready and trigger_long
            fired_short = short_side.ready and trigger_short
            if fired_long and fired_short:
                return (1, False) if long_side.expected_r >= short_side.expected_r else (-1, False)
            return (1 if fired_long else -1 if fired_short else 0), False
        return self._pending_machine(
            state, snapshots, index, long_side, short_side,
            trigger_long=trigger_long, trigger_short=trigger_short,
            vwap=vwap, ema20=ema20,
        )

    def _resolve_immediate(self, long_side: _SideState, short_side: _SideState) -> int:
        if long_side.ready and (
            not short_side.ready or long_side.expected_r >= short_side.expected_r
        ):
            return 1
        if short_side.ready:
            return -1
        return 0

    def _trigger(self, snapshot: DecisionSnapshot, *, bullish: bool) -> bool:
        """trigger_L/S (lines 3010-3011)."""
        bar = snapshot.bar
        close = float(bar.close.value)
        open_ = float(bar.open.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        spread = high - low
        close_loc = (close - low) / spread if spread > 0 else 0.5
        body_fraction = abs(close - open_) / spread if spread > 0 else 0.0
        location = self._params.trigger_close_location
        if bullish:
            strong_close = close > open_ and close_loc >= location
            engulf = flag(snapshot.vector, "statistical.bull_engulfing")
            shift = flag(snapshot.vector, "structure.choch_up") and close > open_
        else:
            strong_close = close < open_ and close_loc <= 1.0 - location
            engulf = flag(snapshot.vector, "statistical.bear_engulfing")
            shift = flag(snapshot.vector, "structure.choch_down") and close < open_
        return (strong_close and body_fraction >= _TRIGGER_BODY_FRACTION) or engulf or shift

    def _retest(
        self,
        snapshot: DecisionSnapshot,
        *,
        vwap: float | None,
        ema20: float | None,
        bullish: bool,
    ) -> bool:
        """retest_L/S (lines 3013-3014)."""
        bar = snapshot.bar
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        vector = snapshot.vector
        if bullish:
            zones = flag(vector, "orderblocks.in_bull_ob") or flag(
                vector, "orderblocks.in_bull_fvg"
            ) or flag(vector, "structure.sweep_low")
            vwap_touch = vwap is not None and low <= vwap < close
            mean_touch = ema20 is not None and low <= ema20
        else:
            zones = flag(vector, "orderblocks.in_bear_ob") or flag(
                vector, "orderblocks.in_bear_fvg"
            ) or flag(vector, "structure.sweep_high")
            vwap_touch = vwap is not None and high >= vwap > close
            mean_touch = ema20 is not None and high >= ema20
        return zones or vwap_touch or mean_touch

    def _micro_bos(
        self, snapshots: list[DecisionSnapshot], index: int, *, bullish: bool
    ) -> bool:
        """micro_bos_L/S (lines 3007-3008)."""
        bars = [snapshot.bar for snapshot in snapshots[: index + 1]]
        highest, lowest = rolling_extremes(bars, index, self._params.micro_bos_length)
        bar = bars[index]
        close = float(bar.close.value)
        open_ = float(bar.open.value)
        if bullish:
            return highest is not None and close > highest and close > open_
        return lowest is not None and close < lowest and close < open_

    def _pending_machine(
        self,
        state: _KernelState,
        snapshots: list[DecisionSnapshot],
        index: int,
        long_side: _SideState,
        short_side: _SideState,
        *,
        trigger_long: bool,
        trigger_short: bool,
        vwap: float | None,
        ema20: float | None,
    ) -> tuple[int, bool]:
        """Retest + Micro BOS state machine (lines 3032-3086)."""
        params = self._params
        snapshot = snapshots[index]
        previous_compression = index >= 1 and flag(
            snapshots[index - 1].vector, "volume.compression"
        )
        if long_side.ready or short_side.ready:
            if long_side.ready and (
                not short_side.ready or long_side.expected_r >= short_side.expected_r
            ):
                state.pending_direction = 1
                state.pending_bar = index
                state.pending_pullback = self._retest(
                    snapshot, vwap=vwap, ema20=ema20, bullish=True
                )
                state.pending_setup = classify_long(
                    snapshot.vector, snapshot.channels,
                    previous_compression=previous_compression,
                )
            elif short_side.ready:
                state.pending_direction = -1
                state.pending_bar = index
                state.pending_pullback = self._retest(
                    snapshot, vwap=vwap, ema20=ema20, bullish=False
                )
                state.pending_setup = classify_short(
                    snapshot.vector, snapshot.channels,
                    previous_compression=previous_compression,
                )
        if state.pending_direction == 0:
            return 0, False
        bullish = state.pending_direction == 1
        side = long_side if bullish else short_side
        opposing = short_side if bullish else long_side
        state.pending_pullback = state.pending_pullback or self._retest(
            snapshot, vwap=vwap, ema20=ema20, bullish=bullish
        )
        age = index - state.pending_bar
        threshold, _ = self._profile(snapshot.vector)
        valid = (
            age <= params.pending_maximum_bars
            and "rvol_gate" not in side.failed
            and "atr_band" not in side.failed
            and "cooldown" not in side.failed
            and "similarity_cooldown" not in side.failed
            and side.probability >= threshold - _PENDING_THRESHOLD_RELIEF
            and side.expected_r >= params.minimum_expected_r * _PENDING_EXPECTANCY_FACTOR
        )
        trigger = trigger_long if bullish else trigger_short
        confirmed = trigger or self._micro_bos(snapshots, index, bullish=bullish)
        opposing_stronger = opposing.ready and opposing.expected_r > side.expected_r
        if age >= 1 and valid and state.pending_pullback and confirmed and not opposing_stronger:
            return state.pending_direction, True
        if age > params.pending_maximum_bars or opposing.ready:
            state.pending_direction = 0
            state.pending_setup = ""
            state.pending_pullback = False
        return 0, False

    # --- Outcome construction ------------------------------------------------------

    def _outcome(
        self,
        state: _KernelState,
        snapshot: DecisionSnapshot,
        index: int,
        fired_direction: int,
        from_pending: bool,
        long_side: _SideState,
        short_side: _SideState,
        uncertainty: float,
        atr: float | None,
        *,
        previous_compression: bool,
    ) -> DecisionOutcome:
        bar_open_ms = snapshot.bar.open_time.epoch_ms
        if fired_direction != 0:
            side = long_side if fired_direction == 1 else short_side
            setup = self._setup_name(
                state, snapshot, fired_direction, from_pending, previous_compression
            )
            signal = self._signal(snapshot, fired_direction, side, atr, setup)
            state.last_signal_bar = index
            state.last_similar_bar = index
            state.last_direction = fired_direction
            suffix = "long" if fired_direction == 1 else "short"
            state.last_channels = tuple(
                read(snapshot.channels, f"{name}_{suffix}") for name in _CHANNELS
            )
            state.pending_direction = 0
            state.pending_setup = ""
            state.pending_pullback = False
            return DecisionOutcome(
                bar_open_ms=bar_open_ms,
                action="signal",
                direction=Direction.LONG if fired_direction == 1 else Direction.SHORT,
                setup=setup,
                signal=signal,
                probability=side.probability,
                uncertainty=uncertainty,
                expected_r=side.expected_r,
                contributors=side.contributors,
                failed_gates=(),
            )
        near = max((long_side, short_side), key=lambda side: side.probability)
        threshold, _ = self._profile(snapshot.vector)
        if near.ready and state.pending_direction != 0:
            # Armed, awaiting pullback/trigger confirmation (audited).
            return DecisionOutcome(
                bar_open_ms=bar_open_ms,
                action="pending",
                direction=(
                    Direction.LONG if state.pending_direction == 1 else Direction.SHORT
                ),
                setup=state.pending_setup,
                signal=None,
                probability=near.probability,
                uncertainty=uncertainty,
                expected_r=near.expected_r,
                contributors=near.contributors,
                failed_gates=(),
            )
        if near.probability >= threshold and near.failed:
            direction = Direction.LONG if near is long_side else Direction.SHORT
            return DecisionOutcome(
                bar_open_ms=bar_open_ms,
                action="veto",
                direction=direction,
                setup="",
                signal=None,
                probability=near.probability,
                uncertainty=uncertainty,
                expected_r=near.expected_r,
                contributors=near.contributors,
                failed_gates=tuple(dict.fromkeys(near.failed)),
            )
        return DecisionOutcome(
            bar_open_ms=bar_open_ms,
            action="stand_aside",
            direction=Direction.NEUTRAL,
            setup="",
            signal=None,
            probability=near.probability,
            uncertainty=uncertainty,
            expected_r=near.expected_r,
            contributors=near.contributors,
            failed_gates=(),
        )

    def _setup_name(
        self,
        state: _KernelState,
        snapshot: DecisionSnapshot,
        direction: int,
        from_pending: bool,
        previous_compression: bool,
    ) -> str:
        if from_pending and state.pending_setup:
            return state.pending_setup
        if direction == 1:
            return classify_long(
                snapshot.vector, snapshot.channels,
                previous_compression=previous_compression,
            )
        return classify_short(
            snapshot.vector, snapshot.channels,
            previous_compression=previous_compression,
        )

    def _signal(
        self,
        snapshot: DecisionSnapshot,
        direction: int,
        side: _SideState,
        atr: float | None,
        setup: str,
    ) -> Signal:
        """Entry/stop/targets (AICE lines 3092-3115)."""
        params = self._params
        bar = snapshot.bar
        close = float(bar.close.value)
        risk_atr = (atr or 0.0) * max(
            read(snapshot.vector, "volume.adaptive_atr_ratio"), 1e-9
        ) or max(atr or 0.0, 1e-9)
        stop = self._stop_price(snapshot, close, risk_atr, bullish=direction == 1)
        risk_points = max(abs(close - stop), 1e-9)
        rr = params.base_risk_reward
        sign = 1.0 if direction == 1 else -1.0
        tp1 = close + sign * risk_points * rr * _TP1_FACTOR
        tp2 = close + sign * risk_points * rr
        tp3 = close + sign * risk_points * rr * _TP3_FACTOR
        target = snapshot.macro_high if direction == 1 else snapshot.macro_low
        if params.liquidity_targets_enabled and target is not None:
            beyond_tp2 = target > tp2 if direction == 1 else target < tp2
            inside_tp3 = target < tp3 if direction == 1 else target > tp3
            if beyond_tp2 and inside_tp3:
                tp3 = target
        return Signal(
            created_at=self._clock.now(),
            exchange=bar.exchange,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            direction=Direction.LONG if direction == 1 else Direction.SHORT,
            probability=Probability(side.probability),
            confidence=Confidence(clamp(side.confidence, 0.0, 1.0)),
            entry_zone=self._zone(close, close),
            stop_zone=self._zone(stop, stop),
            target_zones=(
                self._zone(*sorted((tp1, tp1))),
                self._zone(*sorted((tp2, tp2))),
                self._zone(*sorted((tp3, tp3))),
            ),
            expected_return=ExpectedReturn(side.expected_r),
            risk_reward=RiskReward(rr),
            market_regime=self._regime(snapshot.vector),
            execution_policy=setup,
        )

    def _stop_price(
        self,
        snapshot: DecisionSnapshot,
        close: float,
        risk_atr: float,
        *,
        bullish: bool,
    ) -> float:
        """ATR stop, upgraded to the protected swing when in bounds.

        The AICE Structure Hybrid prefers the order-block boundary; the
        zone store lands with the execution phase, so the protected
        swing branch applies meanwhile (documented in the module note).
        """
        params = self._params
        sign = 1.0 if bullish else -1.0
        atr_stop = close - sign * risk_atr * params.stop_atr_multiple
        if params.stop_model != STOP_STRUCTURE_HYBRID:
            return atr_stop
        swing = snapshot.macro_low if bullish else snapshot.macro_high
        # Chart protected swing approximated by the macro extreme when
        # available; falls back to the ATR stop outside risk bounds.
        if swing is None:
            return atr_stop
        candidate = swing - sign * risk_atr * _STOP_BUFFER_ATR
        risk = (close - candidate) if bullish else (candidate - close)
        max_risk = risk_atr * params.stop_atr_multiple * _STOP_MAX_FACTOR
        min_risk = risk_atr * _STOP_MIN_ATR
        if min_risk < risk <= max_risk:
            return candidate
        return atr_stop

    def _zone(self, lower: float, upper: float) -> PriceZone:
        low, high = sorted((lower, upper))
        return PriceZone(
            lower=Price(Decimal(str(round(low, 8)))),
            upper=Price(Decimal(str(round(high, 8)))),
        )

    def _regime(self, vector: Mapping[str, float]) -> str:
        if flag(vector, "statistical.is_trending"):
            return "trend"
        if flag(vector, "statistical.is_ranging"):
            return "range"
        return "transition"
