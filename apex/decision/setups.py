"""AICE setup classification taxonomy (Book VI spec lines 2775-2830).

Classifies each fired side into the named institutional setup, walking
the AICE priority chain (first match wins) over the stored feature
vector, the persisted evidence channels and the composed cross-family
flags. ``mss`` (market structure shift) is AICE's CHoCH flag: the
structure block raises it exactly when a change of character fires.
"""

from collections.abc import Mapping

from apex.probability.evidence import (
    flag,
    read,
    spring,
    strong_break_down,
    strong_break_up,
    upthrust,
)

CONFLUENCE_LONG = "Confluence Long"
CONFLUENCE_SHORT = "Confluence Short"

# Channel thresholds used by the taxonomy (AICE lines 2786, 2823-2829).
_DNA_THRESHOLD = 0.6
_ZONE_THRESHOLD = 0.5
_STRUCT_THRESHOLD = 0.4
_MTF_THRESHOLD = 0.6


def classify_long(
    vector: Mapping[str, float],
    channels: Mapping[str, float],
    *,
    previous_compression: bool,
) -> str:
    """The named long setup for this bar (AICE priority order)."""
    sweep = flag(vector, "structure.sweep_low")
    mss = flag(vector, "structure.choch_up")
    in_ob = flag(vector, "orderblocks.in_bull_ob")
    in_fvg = flag(vector, "orderblocks.in_bull_fvg")
    fvg_active = read(vector, "orderblocks.bull_fvg_count") > 0
    strong = strong_break_up(vector)
    broke = flag(vector, "structure.bos_up") or mss
    engulf = flag(vector, "statistical.bull_engulfing")
    rules: tuple[tuple[bool, str], ...] = (
        (read(channels, "smt_long") > 0 and sweep and mss, "SMT Turtle Soup Long"),
        (
            flag(vector, "statistical.pin_bull") and sweep and in_ob and mss,
            "Institutional Long",
        ),
        (sweep and engulf and broke and fvg_active, "Turtle Soup Long"),
        (
            sweep and in_ob and mss and read(channels, "dna_long") > _DNA_THRESHOLD,
            "OB Reversal Long",
        ),
        (flag(vector, "orderblocks.bull_breaker") and mss, "Breaker Long"),
        (spring(vector) and flag(vector, "volume.selling_climax"), "Wyckoff Spring"),
        (previous_compression and strong, "Compression Breakout Long"),
        (
            flag(vector, "structure.in_discount") and sweep and mss and in_ob,
            "Premium/Discount Long",
        ),
        (
            flag(vector, "statistical.hammer")
            and flag(vector, "structure.equal_lows")
            and sweep
            and mss,
            "High-Probability Reversal Long",
        ),
        (strong and fvg_active and in_ob, "FVG Continuation Long"),
        (
            flag(vector, "orderblocks.bpr_bull")
            and read(channels, "zone_long") > _ZONE_THRESHOLD
            and read(channels, "structure_long") > _STRUCT_THRESHOLD,
            "BPR Rebalance Long",
        ),
        (
            in_ob and in_fvg and read(channels, "mtf_long") > _MTF_THRESHOLD,
            "Nested OB/FVG Long",
        ),
    )
    for matched, name in rules:
        if matched:
            return name
    return CONFLUENCE_LONG


def classify_short(
    vector: Mapping[str, float],
    channels: Mapping[str, float],
    *,
    previous_compression: bool,
) -> str:
    """The named short setup for this bar (AICE priority order)."""
    sweep = flag(vector, "structure.sweep_high")
    mss = flag(vector, "structure.choch_down")
    in_ob = flag(vector, "orderblocks.in_bear_ob")
    in_fvg = flag(vector, "orderblocks.in_bear_fvg")
    fvg_active = read(vector, "orderblocks.bear_fvg_count") > 0
    strong = strong_break_down(vector)
    broke = flag(vector, "structure.bos_down") or mss
    engulf = flag(vector, "statistical.bear_engulfing")
    rules: tuple[tuple[bool, str], ...] = (
        (read(channels, "smt_short") > 0 and sweep and mss, "SMT Turtle Soup Short"),
        (
            flag(vector, "statistical.pin_bear") and sweep and in_ob and mss,
            "Institutional Short",
        ),
        (sweep and engulf and broke and fvg_active, "Turtle Soup Short"),
        (
            sweep and in_ob and mss and read(channels, "dna_short") > _DNA_THRESHOLD,
            "OB Reversal Short",
        ),
        (flag(vector, "orderblocks.bear_breaker") and mss, "Breaker Short"),
        (upthrust(vector) and flag(vector, "volume.buying_climax"), "Wyckoff Upthrust"),
        (previous_compression and strong, "Compression Breakout Short"),
        (
            flag(vector, "structure.in_premium") and sweep and mss and in_ob,
            "Premium/Discount Short",
        ),
        (
            flag(vector, "statistical.shooting_star")
            and flag(vector, "structure.equal_highs")
            and sweep
            and mss,
            "High-Probability Reversal Short",
        ),
        (strong and fvg_active and in_ob, "FVG Continuation Short"),
        (
            flag(vector, "orderblocks.bpr_bear")
            and read(channels, "zone_short") > _ZONE_THRESHOLD
            and read(channels, "structure_short") > _STRUCT_THRESHOLD,
            "BPR Rebalance Short",
        ),
        (
            in_ob and in_fvg and read(channels, "mtf_short") > _MTF_THRESHOLD,
            "Nested OB/FVG Short",
        ),
    )
    for matched, name in rules:
        if matched:
            return name
    return CONFLUENCE_SHORT
