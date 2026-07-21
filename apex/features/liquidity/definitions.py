"""Registry declarations for the liquidity family."""

from apex.core.versioning import SemanticVersion
from apex.features.liquidity.engine import FAMILY, LiquidityParams
from apex.features.registry import FeatureDefinition

_VERSION = SemanticVersion(1, 0, 0)

_DESCRIPTIONS: dict[str, str] = {
    "liquidity.pool_high_confidence": (
        "Decayed confidence that liquidity rests above (equal highs); reset when swept"
    ),
    "liquidity.pool_low_confidence": (
        "Decayed confidence that liquidity rests below (equal lows); reset when swept"
    ),
    "liquidity.resting_high": (
        "Composite resting liquidity above: pool, scale equals, extreme proximity"
    ),
    "liquidity.resting_low": (
        "Composite resting liquidity below: pool, scale equals, extreme proximity"
    ),
    "liquidity.equal_highs_internal": (
        "New internal-scale swing high within ATR tolerance of the previous one"
    ),
    "liquidity.equal_lows_internal": (
        "New internal-scale swing low within ATR tolerance of the previous one"
    ),
    "liquidity.equal_highs_external": (
        "New external-scale swing high within ATR tolerance of the previous one"
    ),
    "liquidity.equal_lows_external": (
        "New external-scale swing low within ATR tolerance of the previous one"
    ),
    "liquidity.external_high_proximity": (
        "Closeness of price to the external range high, in ATR units"
    ),
    "liquidity.external_low_proximity": (
        "Closeness of price to the external range low, in ATR units"
    ),
    "liquidity.sweep_high_efficiency": (
        "Rejection strength of a high sweep: upper wick share of the bar range"
    ),
    "liquidity.sweep_low_efficiency": (
        "Rejection strength of a low sweep: recovery share of the bar range"
    ),
    "liquidity.stop_hunt_high": "High sweep through equal highs (engineered stop run)",
    "liquidity.stop_hunt_low": "Low sweep through equal lows (engineered stop run)",
    "liquidity.inducement_long": "Low sweep aligned with non-bearish trend and internal bias",
    "liquidity.inducement_short": "High sweep aligned with non-bullish trend and internal bias",
}


def liquidity_definitions(params: LiquidityParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the liquidity family."""
    defaults = {
        "chart_lookback": params.chart_lookback,
        "internal_lookback": params.internal_lookback,
        "external_lookback": params.external_lookback,
        "atr_length": params.atr_length,
        "equal_tolerance_atr": params.equal_tolerance_atr,
        "liquidity_decay": params.liquidity_decay,
        "ema_length": params.ema_length,
    }
    return tuple(
        FeatureDefinition(
            name=name,
            family=FAMILY,
            description=description,
            version=_VERSION,
            default_params=defaults,
        )
        for name, description in _DESCRIPTIONS.items()
    )
