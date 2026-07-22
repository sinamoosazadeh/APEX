"""AICE evidence channels computed from a stored feature vector.

Faithful port of the thirteen ``ev_*`` confluence composites (Book VI
spec lines 2583-2669), re-expressed over the Phase 4 feature registry:
every Pine series input maps to a stored feature name, so the evidence
is a pure function of one bar's persisted vector (plus the structure
momentum fold supplied by the engine).

Cross-family compositions AICE defines inline are assembled here from
their stored ingredients exactly as documented in the feature layer:
``spring/upthrust`` (sweep x opposing close x expansion), ``sos/sow``
(strong break x aggression) and ``effort_result`` (high RVOL into a
narrow bar).

Deferred inputs (documented, AICE-gated or later-phase):
- Kalman terms (``use_kalman_signal_filter`` gates them off in AICE;
  the Kalman filter itself is unmigrated) contribute 0.
- The crypto dominance context (``use_crypto_ctx``) arrives with the
  multi-exchange expansion; its disabled branch contributes 0.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from apex.features.calculations import clamp

# ev_struct shape (AICE lines 2588-2589).
_STRUCT_STRONG, _STRUCT_WEAK, _STRUCT_TREND = 1.0, 0.55, 0.35
_STRUCT_QUALITY_BASE, _STRUCT_QUALITY_SPAN = 0.55, 0.45
_STRUCT_MOMENTUM_WEIGHT = 0.15
# ev_liq shape (lines 2591-2592).
_LIQ_BASE, _LIQ_EFFICIENCY, _LIQ_RESTING, _LIQ_EVENT = 0.40, 0.25, 0.20, 0.10
# ev_zone shape (lines 2599-2600).
_ZONE_PD, _ZONE_OTE, _ZONE_HTF, _ZONE_VWAP = 0.40, 0.30, 0.20, 0.10
_ZONE_VWAP_Z = 1.25
# ev_delta shape (lines 2607-2608).
_DELTA_AGGRESSION, _DELTA_ABSORPTION, _DELTA_BREAK, _DELTA_CLIMAX = 0.40, 0.25, 0.15, 0.20
# ev_seq flip bonus (lines 2611-2612).
_SEQ_FLIP = 0.15
# ev_trend VWAP bonus (lines 2614-2615); the Kalman 0.15 term is gated off.
_TREND_VWAP = 0.12
# ev_mtf shape (lines 2618-2619).
_MTF_INTERNAL, _MTF_CHART, _MTF_EXTERNAL, _MTF_MACRO = 0.22, 0.26, 0.22, 0.15
# ev_profile shape (lines 2623-2624).
_PROFILE_SIDE, _PROFILE_ACCEPTANCE, _PROFILE_VWAP, _PROFILE_NEAR = 0.40, 0.30, 0.20, 0.10
_PROFILE_NEAR_ATR = 1.0


def read(vector: Mapping[str, float], name: str) -> float:
    """A feature's raw value; 0.0 when absent (neutral absence)."""
    return vector.get(name, 0.0)


def flag(vector: Mapping[str, float], name: str) -> bool:
    """A binary feature as a boolean."""
    return vector.get(name, 0.0) > 0.5


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceChannels:
    """The thirteen AICE evidence channels, long and short."""

    structure_long: float
    structure_short: float
    liquidity_long: float
    liquidity_short: float
    orderblock_long: float
    orderblock_short: float
    fvg_long: float
    fvg_short: float
    zone_long: float
    zone_short: float
    dna_long: float
    dna_short: float
    kinetic_long: float
    kinetic_short: float
    delta_long: float
    delta_short: float
    sequence_long: float
    sequence_short: float
    trend_long: float
    trend_short: float
    mtf_long: float
    mtf_short: float
    smt_long: float
    smt_short: float
    profile_long: float
    profile_short: float

    def pairs(self) -> tuple[tuple[float, float], ...]:
        """(long, short) per channel, in the AICE w0..w12 order."""
        return (
            (self.structure_long, self.structure_short),
            (self.liquidity_long, self.liquidity_short),
            (self.orderblock_long, self.orderblock_short),
            (self.fvg_long, self.fvg_short),
            (self.zone_long, self.zone_short),
            (self.dna_long, self.dna_short),
            (self.kinetic_long, self.kinetic_short),
            (self.delta_long, self.delta_short),
            (self.sequence_long, self.sequence_short),
            (self.trend_long, self.trend_short),
            (self.mtf_long, self.mtf_short),
            (self.smt_long, self.smt_short),
            (self.profile_long, self.profile_short),
        )


def strong_break_up(vector: Mapping[str, float]) -> bool:
    """AICE line 1180: displacement break upward."""
    broke = flag(vector, "structure.bos_up") or flag(vector, "structure.choch_up")
    return broke and flag(vector, "structure.is_displacement")


def strong_break_down(vector: Mapping[str, float]) -> bool:
    """AICE line 1181: displacement break downward."""
    broke = flag(vector, "structure.bos_down") or flag(vector, "structure.choch_down")
    return broke and flag(vector, "structure.is_displacement")


def spring(vector: Mapping[str, float]) -> bool:
    """AICE line 1719: low sweep, up close, range expansion."""
    return (
        flag(vector, "structure.sweep_low")
        and read(vector, "statistical.direction") > 0
        and flag(vector, "volume.expansion")
    )


def upthrust(vector: Mapping[str, float]) -> bool:
    """AICE line 1720: high sweep, down close, range expansion."""
    return (
        flag(vector, "structure.sweep_high")
        and read(vector, "statistical.direction") < 0
        and flag(vector, "volume.expansion")
    )


def effort_result(vector: Mapping[str, float]) -> bool:
    """AICE line 1723: heavy volume achieving a below-average range."""
    return read(vector, "volume.rvol") > 1.5 and flag(vector, "volume.narrow_range")


def compute_evidence(
    vector: Mapping[str, float], struct_momentum: float
) -> EvidenceChannels:
    """All thirteen channels for one bar's feature vector."""
    structure_long, structure_short = _structure(vector, struct_momentum)
    liquidity_long, liquidity_short = _liquidity(vector)
    zone_long, zone_short = _zone(vector)
    delta_long, delta_short = _delta(vector)
    trend_long, trend_short = _trend(vector)
    mtf_long, mtf_short = _mtf(vector)
    profile_long, profile_short = _profile(vector)
    return EvidenceChannels(
        structure_long=structure_long,
        structure_short=structure_short,
        liquidity_long=liquidity_long,
        liquidity_short=liquidity_short,
        orderblock_long=read(vector, "orderblocks.ob_long_confidence"),
        orderblock_short=read(vector, "orderblocks.ob_short_confidence"),
        fvg_long=read(vector, "orderblocks.fvg_long_confidence"),
        fvg_short=read(vector, "orderblocks.fvg_short_confidence"),
        zone_long=zone_long,
        zone_short=zone_short,
        dna_long=read(vector, "statistical.dna_bull"),
        dna_short=read(vector, "statistical.dna_bear"),
        kinetic_long=read(vector, "statistical.kinetic_long"),
        kinetic_short=read(vector, "statistical.kinetic_short"),
        delta_long=delta_long,
        delta_short=delta_short,
        sequence_long=clamp(
            read(vector, "statistical.sequence_bull_bias")
            + (_SEQ_FLIP if flag(vector, "statistical.direction_flip_bull") else 0.0),
            0.0,
            1.0,
        ),
        sequence_short=clamp(
            read(vector, "statistical.sequence_bear_bias")
            + (_SEQ_FLIP if flag(vector, "statistical.direction_flip_bear") else 0.0),
            0.0,
            1.0,
        ),
        trend_long=trend_long,
        trend_short=trend_short,
        mtf_long=mtf_long,
        mtf_short=mtf_short,
        smt_long=read(vector, "smt.bull_confidence"),
        smt_short=read(vector, "smt.bear_confidence"),
        profile_long=profile_long,
        profile_short=profile_short,
    )


def _structure(vector: Mapping[str, float], momentum: float) -> tuple[float, float]:
    quality = read(vector, "structure.break_quality")
    scale = _STRUCT_QUALITY_BASE + _STRUCT_QUALITY_SPAN * quality
    trend = read(vector, "structure.trend_direction")
    weak_up = flag(vector, "structure.bos_up") and not flag(
        vector, "structure.is_displacement"
    )
    weak_down = flag(vector, "structure.bos_down") and not flag(
        vector, "structure.is_displacement"
    )
    base_long = (
        _STRUCT_STRONG
        if strong_break_up(vector)
        else _STRUCT_WEAK
        if weak_up
        else _STRUCT_TREND
        if trend > 0
        else 0.0
    )
    base_short = (
        _STRUCT_STRONG
        if strong_break_down(vector)
        else _STRUCT_WEAK
        if weak_down
        else _STRUCT_TREND
        if trend < 0
        else 0.0
    )
    long_side = clamp(
        base_long * scale + max(momentum, 0.0) * _STRUCT_MOMENTUM_WEIGHT, 0.0, 1.0
    )
    short_side = clamp(
        base_short * scale + max(-momentum, 0.0) * _STRUCT_MOMENTUM_WEIGHT, 0.0, 1.0
    )
    return long_side, short_side


def _liquidity(vector: Mapping[str, float]) -> tuple[float, float]:
    sprung = spring(vector)
    thrust = upthrust(vector)
    long_side = 0.0
    if flag(vector, "structure.sweep_low") or sprung:
        long_side = clamp(
            _LIQ_BASE
            + read(vector, "liquidity.sweep_low_efficiency") * _LIQ_EFFICIENCY
            + read(vector, "liquidity.resting_low") * _LIQ_RESTING
            + (_LIQ_EVENT if sprung else 0.0)
            + (_LIQ_EVENT if flag(vector, "liquidity.stop_hunt_low") else 0.0)
            + (_LIQ_EVENT if flag(vector, "liquidity.inducement_long") else 0.0),
            0.0,
            1.0,
        )
    short_side = 0.0
    if flag(vector, "structure.sweep_high") or thrust:
        short_side = clamp(
            _LIQ_BASE
            + read(vector, "liquidity.sweep_high_efficiency") * _LIQ_EFFICIENCY
            + read(vector, "liquidity.resting_high") * _LIQ_RESTING
            + (_LIQ_EVENT if thrust else 0.0)
            + (_LIQ_EVENT if flag(vector, "liquidity.stop_hunt_high") else 0.0)
            + (_LIQ_EVENT if flag(vector, "liquidity.inducement_short") else 0.0),
            0.0,
            1.0,
        )
    return long_side, short_side


def _zone(vector: Mapping[str, float]) -> tuple[float, float]:
    vwap_z = read(vector, "volume.vwap_deviation_z")
    long_side = clamp(
        (_ZONE_PD if flag(vector, "structure.in_discount") else 0.0)
        + (_ZONE_OTE if flag(vector, "structure.in_ote_long") else 0.0)
        + (_ZONE_HTF if flag(vector, "htf.in_discount") else 0.0)
        + (_ZONE_VWAP if vwap_z < -_ZONE_VWAP_Z else 0.0),
        0.0,
        1.0,
    )
    short_side = clamp(
        (_ZONE_PD if flag(vector, "structure.in_premium") else 0.0)
        + (_ZONE_OTE if flag(vector, "structure.in_ote_short") else 0.0)
        + (_ZONE_HTF if flag(vector, "htf.in_premium") else 0.0)
        + (_ZONE_VWAP if vwap_z > _ZONE_VWAP_Z else 0.0),
        0.0,
        1.0,
    )
    return long_side, short_side


def _delta(vector: Mapping[str, float]) -> tuple[float, float]:
    aggression = read(vector, "volume.aggression")
    long_side = clamp(
        (clamp(aggression, 0.0, 1.0) * _DELTA_AGGRESSION if aggression > 0 else 0.0)
        + (_DELTA_ABSORPTION if flag(vector, "volume.absorption_buy") else 0.0)
        + (_DELTA_BREAK if strong_break_up(vector) and aggression > 0 else 0.0)
        + (_DELTA_CLIMAX if flag(vector, "volume.selling_climax") else 0.0),
        0.0,
        1.0,
    )
    short_side = clamp(
        (clamp(-aggression, 0.0, 1.0) * _DELTA_AGGRESSION if aggression < 0 else 0.0)
        + (_DELTA_ABSORPTION if flag(vector, "volume.absorption_sell") else 0.0)
        + (_DELTA_BREAK if strong_break_down(vector) and aggression < 0 else 0.0)
        + (_DELTA_CLIMAX if flag(vector, "volume.buying_climax") else 0.0),
        0.0,
        1.0,
    )
    return long_side, short_side


def _trend(vector: Mapping[str, float]) -> tuple[float, float]:
    slope = read(vector, "volume.momentum_slope")
    above_vwap = read(vector, "volume.vwap_deviation_atr") > 0
    long_side = clamp(
        (slope if flag(vector, "volume.momentum_bull") else 0.0)
        + (_TREND_VWAP if above_vwap else 0.0),
        0.0,
        1.0,
    )
    short_side = clamp(
        ((1.0 - slope) if flag(vector, "volume.momentum_bear") else 0.0)
        + (_TREND_VWAP if not above_vwap else 0.0),
        0.0,
        1.0,
    )
    return long_side, short_side


def _mtf(vector: Mapping[str, float]) -> tuple[float, float]:
    internal = read(vector, "structure.internal_bias")
    external = read(vector, "structure.external_bias")
    trend = read(vector, "structure.trend_direction")
    macro1 = read(vector, "htf.macro1_bias")
    macro2 = read(vector, "htf.macro2_bias")
    long_side = clamp(
        (_MTF_INTERNAL if internal > 0 else 0.0)
        + (_MTF_CHART if trend > 0 else 0.0)
        + (_MTF_EXTERNAL if external > 0 else 0.0)
        + (_MTF_MACRO if macro1 > 0 else 0.0)
        + (_MTF_MACRO if macro2 > 0 else 0.0),
        0.0,
        1.0,
    )
    short_side = clamp(
        (_MTF_INTERNAL if internal < 0 else 0.0)
        + (_MTF_CHART if trend < 0 else 0.0)
        + (_MTF_EXTERNAL if external < 0 else 0.0)
        + (_MTF_MACRO if macro1 < 0 else 0.0)
        + (_MTF_MACRO if macro2 < 0 else 0.0),
        0.0,
        1.0,
    )
    return long_side, short_side


def _profile(vector: Mapping[str, float]) -> tuple[float, float]:
    # AICE gates ev_profile on a known POC (lines 2623-2624); a vector
    # without the profile features reads as "no profile" -> 0 evidence.
    if "volume.poc_acceptance" not in vector:
        return 0.0, 0.0
    acceptance = read(vector, "volume.poc_acceptance")
    near = read(vector, "volume.poc_distance_atr") < _PROFILE_NEAR_ATR
    above_vwap = read(vector, "volume.vwap_deviation_atr") > 0
    above_poc = flag(vector, "volume.above_poc")
    long_side = clamp(
        (_PROFILE_SIDE if above_poc else 0.0)
        + acceptance * _PROFILE_ACCEPTANCE
        + (_PROFILE_VWAP if above_vwap else 0.0)
        + (_PROFILE_NEAR if near else 0.0),
        0.0,
        1.0,
    )
    short_side = clamp(
        (_PROFILE_SIDE if not above_poc else 0.0)
        + acceptance * _PROFILE_ACCEPTANCE
        + (_PROFILE_VWAP if not above_vwap else 0.0)
        + (_PROFILE_NEAR if near else 0.0),
        0.0,
        1.0,
    )
    return long_side, short_side
